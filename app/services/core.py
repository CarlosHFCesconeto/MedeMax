"""Headless application service. One polling worker per serial bus/TCP device.
UI consumes snapshots; network/database operations never require a Qt event loop.
"""
from collections import deque
from concurrent.futures import Future
from dataclasses import replace
import logging
import queue
import threading
import time
from uuid import uuid4
from .trend import TrendBuffer
from ..models import Device, Tag, AlarmRule, Sample
from ..profiles import MEASUREMENT_MAP, measurement_tags, read_plan
from ..codec import decode, encode
from ..communication.transports import make_transport, ModbusError, Simulator, validate_range
from .alarms import AlarmEngine

log = logging.getLogger(__name__)


class Core:
    def __init__(self, repository):
        self.repo = repository
        self.lock = threading.RLock()
        self.latest = {}
        self.buffers = {}
        self.status = {}
        self.diagnostics = deque(maxlen=1000)
        self.trace_enabled = False
        self.workers = []
        self.stop_event = threading.Event()
        self.history_queue = queue.Queue(maxsize=20000)
        self.dropped_history = 0
        self.storage_error = ''
        self.pending_writes = set()
        self.writer = None
        self.reload()

    def reload(self):
        if self.running: raise RuntimeError('Pare a aquisição antes de alterar configurações')
        self.devices = {d.id:d for d in self.repo.load(Device)}
        self.tags = {t.id:t for t in self.repo.load(Tag)}
        self.rules = self.repo.load(AlarmRule)
        self.alarms = AlarmEngine(self.repo,self.rules)
        with self.lock:
            self.latest.clear(); self.buffers.clear(); self.status.clear()

    @property
    def running(self): return any(w.is_alive() for w in self.workers)

    def save(self, obj):
        if self.running: raise RuntimeError('Pare a aquisição antes de configurar')
        if isinstance(obj,Tag) and obj.device_id not in self.devices: raise ValueError('Dispositivo inexistente')
        if isinstance(obj,AlarmRule) and obj.tag_id not in self.tags: raise ValueError('Tag inexistente')
        obj.validate()
        self.repo.save(obj)
        self.reload()

    def device_removal_plan(self, identifier):
        if self.running or (self.writer and self.writer.is_alive()):
            raise RuntimeError('Pare a aquisição e aguarde a gravação do histórico antes de excluir')
        return self.repo.device_removal_plan(identifier)

    def remove(self, cls, identifier, expected_dependencies=None):
        if self.running or (self.writer and self.writer.is_alive()): raise RuntimeError('Pare a aquisição e aguarde a gravação do histórico antes de excluir')
        if cls is Device:
            plan=self.repo.remove_device(identifier,time.time(),expected_dependencies)
            self.reload()
            log.info('Dispositivo excluído: %s; %d tags; %d regras; %d alarmes ativos encerrados por exclusão',
                     plan['name'],len(plan['tag_ids']),len(plan['rule_ids']),plan['active_alarms'])
            return plan
        if cls is Tag and any(r.tag_id==identifier for r in self.rules): raise ValueError('Remova primeiro as regras dessa tag')
        if cls is AlarmRule and identifier in self.alarms.active: raise ValueError('Regra possui evento ativo; normalize antes de excluir')
        self.repo.remove(cls,identifier)
        self.reload()

    def start(self):
        if self.running or (self.writer and self.writer.is_alive()): raise RuntimeError('Aquisição já em execução ou encerrando')
        self.reload()
        groups = {}
        for d in self.devices.values():
            d.validate()
            if d.enabled: groups.setdefault(d.bus_key(),[]).append(d)
        for devices in groups.values():
            first=devices[0]
            if first.transport == 'RTU':
                settings=lambda d:(d.baudrate,d.parity,d.bytesize,d.stopbits,d.timeout,d.retries)
                if any(settings(d)!=settings(first) for d in devices): raise ValueError('Dispositivos na mesma COM precisam de parâmetros seriais/timeout/retries iguais')
        for t in self.tags.values(): t.validate()
        self.stop_event.clear()
        self.writer = threading.Thread(target=self._history_writer,name='historian',daemon=False)
        self.writer.start()
        self.workers = [BusWorker(self,devices) for devices in groups.values()]
        for w in self.workers: w.start()
        log.info('Aquisição iniciada: %d conexões',len(groups))

    def request_stop(self):
        self.stop_event.set()

    def stop(self, timeout=60):
        self.request_stop()
        deadline=time.monotonic()+timeout
        for w in self.workers: w.join(max(0,deadline-time.monotonic()))
        if self.running: return False
        if self.writer: self.writer.join(max(0,deadline-time.monotonic()))
        log.info('Aquisição encerrada')
        return not (self.writer and self.writer.is_alive())

    def _history_writer(self):
        last_prune=0
        while not self.stop_event.is_set() or self.running or not self.history_queue.empty():
            batch=[]
            try: batch.append(self.history_queue.get(timeout=.2))
            except queue.Empty: pass
            while len(batch)<500:
                try: batch.append(self.history_queue.get_nowait())
                except queue.Empty: break
            try:
                if batch: self.repo.append(batch)
                if time.monotonic()-last_prune>60:
                    days=int(self.repo.setting('retention_days',60))
                    self.repo.prune(time.time()-days*86400)
                    last_prune=time.monotonic()
            except Exception as e:
                log.exception('Falha no histórico')
                with self.lock:
                    self.storage_error=str(e); self.dropped_history+=len(batch)

    def publish(self, sample, elapsed):
        with self.lock:
            self.latest[sample.tag_id]=sample
            buf=self.buffers.setdefault(sample.tag_id,TrendBuffer())
            buf.append((sample.timestamp,sample.value if sample.quality=='OK' else float('nan')))
            status=self.status.setdefault(sample.device_id,{'state':'Sem leitura','last':None,'average_ms':0,'errors':0,'reads':0})
            status['state']='Online' if sample.quality=='OK' else sample.quality
            status['reads']+=1
            status['average_ms']+= (elapsed-status['average_ms'])/status['reads']
            if sample.quality=='OK': status['last']=sample.timestamp
            else: status['errors']+=1
        # Do not hold the snapshot lock across disk I/O: the UI must remain responsive.
        try: self.alarms.process(sample)
        except Exception as e:
            with self.lock: self.storage_error=str(e)
            log.exception('Falha persistindo alarme')
        tag=self.tags[sample.tag_id]
        if tag.history:
            try: self.history_queue.put_nowait(sample)
            except queue.Full:
                with self.lock: self.dropped_history+=1

    def snapshot(self):
        with self.lock: return dict(self.latest),{k:dict(v) for k,v in self.status.items()}

    def graph(self, tag_id, seconds):
        cutoff=time.time()-seconds
        with self.lock:
            buf=self.buffers.get(tag_id)
            return buf.points(cutoff,seconds) if buf else []

    def trace(self, device, direction, detail):
        if self.trace_enabled:
            with self.lock: self.diagnostics.append((time.time(),device,direction,detail))

    def write(self, tag_id, value):
        tag=self.tags[tag_id]
        if not tag.enabled: raise ValueError('Tag inativa')
        encoded=encode(value,tag)
        device=self.devices[tag.device_id]
        if not device.enabled or self.stop_event.is_set(): raise RuntimeError('Aquisição parada/dispositivo inativo')
        sample=self.latest.get(tag_id)
        if not sample or sample.quality!='OK' or time.time()-sample.timestamp>max(5,device.interval_ms/1000*3): raise RuntimeError('É necessária uma leitura recente OK antes de escrever')
        worker=next((w for w in self.workers if device in w.devices and w.is_alive()),None)
        if not worker: raise RuntimeError('Dispositivo sem aquisição ativa')
        identifier=uuid4().hex
        future=Future()
        # Audit must succeed before enqueue; no command is sent if audit fails.
        with self.lock:
            if tag_id in self.pending_writes: raise RuntimeError('Já existe uma escrita pendente para esta tag')
            self.pending_writes.add(tag_id)
        def release(_):
            with self.lock: self.pending_writes.discard(tag_id)
        future.add_done_callback(release)
        try:
            self.repo.command(identifier,time.time(),tag_id,float(value),'Pendente')
        except Exception:
            release(None)
            raise
        try: worker.commands.put_nowait((identifier,time.monotonic(),tag,float(value),encoded,future))
        except queue.Full:
            release(None)
            self.repo.command(identifier,time.time(),tag_id,float(value),'Cancelado','Fila cheia')
            raise RuntimeError('Fila de comandos cheia')
        return future

    def set_simulation(self, mode):
        if mode not in ('normal','timeout','offline','alarme'): raise ValueError(mode)
        for w in self.workers:
            if isinstance(w.transport,Simulator): w.transport.mode=mode

    def demo_multi(self):
        """Idempotent explicit synthetic installation; no real map implied."""
        if self.running: raise RuntimeError('Pare a aquisição primeiro')
        for n in range(1,4):
            identifier=f'medemax-sim-three-{n}'
            if identifier in self.devices: continue
            d=Device(id=identifier,name=f'Medidor {n} • SIM',transport='SIM',unit_id=n,interval_ms=100,description='Demonstração trifásica; mapa fictício 100–107; tensão do neutro com referência fictícia.')
            self.save(d)
            for k,phase in enumerate(('L1','L2','L3','N')):
                for j,(quantity,scale,unit) in enumerate((('Tensão',.1,'V'),('Corrente',.01,'A'))):
                    tag=Tag(name=f'{quantity} {phase}',device_id=d.id,address=100+2*k+j,scale=scale,unit=unit)
                    self.save(tag)
                    if k==0 and j==0:
                        self.save(AlarmRule(name=f'Sobretensão • Medidor {n} • SIM',tag_id=tag.id,threshold=240,severity='Alta',message='Tensão simulada acima de 240 V'))

    def apply_measurement_map(self, device_id, power_type='UINT16', factor_type='UINT16', group_reads=True):
        if self.running or (self.writer and self.writer.is_alive()):
            raise RuntimeError('Pare a aquisição antes de aplicar o mapa')
        device = self.devices[device_id]
        new_tags = []
        expected = measurement_tags(device_id, power_type, factor_type)
        for tag in expected:
            matches = [t for t in self.tags.values() if t.device_id == device_id and t.function == 4
                       and t.address < tag.address + tag.count and t.address + t.count > tag.address]
            if matches:
                fields = ('address', 'count', 'data_type', 'scale', 'offset', 'unit', 'byte_order', 'word_order', 'writable', 'enabled', 'polling', 'history')
                if len(matches) != 1 or any(getattr(matches[0], k) != getattr(tag, k) for k in fields):
                    raise ValueError(f'Já existe uma tag incompatível em FC04 @{tag.address}. Revise em Tags ou use outro dispositivo; nada foi alterado.')
            else:
                new_tags.append(tag)
        updated = replace(device, read_blocks=group_reads, measurement_profile=MEASUREMENT_MAP)
        self.repo.save_many([updated, *new_tags])
        self.reload()
        return len(new_tags)

    def demo_measurement_map(self):
        if self.running: raise RuntimeError('Pare a aquisição primeiro')
        identifier = 'medemax-input26-simulation'
        if identifier not in self.devices:
            self.save(Device(id=identifier, name='Medidor 26 variáveis • SIM', transport='SIM',
                             interval_ms=500, description='Simulação do mapa FC04 0–25; valores sintéticos.'))
        return self.apply_measurement_map(identifier)

    def demo(self):
        if self.running: raise RuntimeError('Pare a aquisição primeiro')
        if any(d.transport=='SIM' for d in self.devices.values()): return
        device=Device(name='Bancada simulada (mapa fictício)',transport='SIM',interval_ms=500)
        self.save(device)
        for name,address,scale,unit in [('Tensão',0,.1,'V'),('Corrente',1,.01,'A'),('Potência',2,1,'W'),('Temperatura',3,.1,'°C')]:
            tag=Tag(name=name+' • SIM',device_id=device.id,address=address,scale=scale,unit=unit,writable=True,write_min=0,write_max=10000)
            self.save(tag)
            if address==3: self.save(AlarmRule(name='Temperatura alta • SIM',tag_id=tag.id,threshold=80,severity='Alta',message='Temperatura simulada acima de 80 °C'))


class BusWorker(threading.Thread):
    def __init__(self, core, devices):
        super().__init__(name='bus-'+devices[0].name,daemon=False)
        self.core=core; self.devices=devices
        self.commands=queue.Queue(maxsize=16)
        self.transport=make_transport(devices[0],lambda direction,data:core.trace(devices[0].name,direction,data))
        self.next_due={d.id:0 for d in devices}
        self.failures={d.id:0 for d in devices}

    def run(self):
        c=self.core
        log.info('Abrindo transporte %s %s',self.devices[0].transport,self.devices[0].name)
        try:
            while not c.stop_event.is_set():
                self._commands()
                for device in self.devices:
                    if c.stop_event.is_set(): break
                    if time.monotonic()<self.next_due[device.id]: continue
                    cycle_started=time.monotonic()
                    failed=False
                    failure=None
                    tags = [t for t in c.tags.values() if t.device_id == device.id and t.enabled and t.polling]
                    for function, address, count, members in read_plan(tags, device.read_blocks):
                        if c.stop_event.is_set(): break
                        started=time.monotonic(); block=(); detail=''
                        try:
                            if failure: raise failure
                            block=tuple(self.transport.read(device.unit_id,function,address,count))
                            if len(block) != count: raise ModbusError('Resposta incompleta')
                            quality='OK'
                        except TimeoutError as e: quality='Timeout'; detail=str(e); failure=e
                        except (ConnectionError,OSError) as e: quality='Offline'; detail=str(e); failure=e
                        except Exception as e: quality='Erro Modbus'; detail=str(e)
                        elapsed=(time.monotonic()-started)*1000
                        timestamp=time.time()
                        c.trace(device.name,'OP',f'Unit {device.unit_id} FC{function:02} @{address} n={count} {elapsed:.1f}ms {quality} {detail}')
                        for tag in members:
                            raw=(); value=None; tag_quality=quality; tag_detail=detail
                            if quality=='OK':
                                offset=tag.address-address
                                raw=block[offset:offset+tag.count]
                                try: value=decode(raw,tag)
                                except Exception as e: tag_quality='Erro Modbus'; tag_detail=str(e)
                            if tag_quality!='OK': failed=True
                            c.publish(Sample(timestamp,tag.id,device.id,value,tag_quality,raw,tag_detail),elapsed)
                    if failed:
                        with c.lock:
                            if device.id in c.status:
                                c.status[device.id]['state'] = ('Timeout' if isinstance(failure,TimeoutError) else 'Offline') if failure else 'Erro Modbus'
                        self.failures[device.id]+=1
                        if failure: self.transport.close()
                        if self.failures[device.id] in (1,5,20): log.warning('Falha %s; reconexão controlada (%d)',device.name,self.failures[device.id])
                    else:
                        if self.failures[device.id]: log.info('Comunicação restabelecida: %s',device.name)
                        self.failures[device.id]=0
                    backoff=min(30,2**min(5,self.failures[device.id]-1)) if failed else 0
                    self.next_due[device.id]=max(cycle_started+device.interval_ms/1000,time.monotonic()+backoff)
                c.stop_event.wait(.005)
        except Exception:
            log.exception('Worker interrompido')
        finally:
            self.transport.close()
            self._commands(cancel=True)
            log.info('Transporte fechado: %s',self.devices[0].name)

    def _commands(self,cancel=False):
        while True:
            try: identifier,queued,tag,value,encoded,future=self.commands.get_nowait()
            except queue.Empty: break
            detail=''; result='Cancelado'
            try:
                if cancel or self.core.stop_event.is_set() or time.monotonic()-queued>3: raise RuntimeError('Comando cancelado/expirado; não enviado')
                d=self.core.devices[tag.device_id]
                sample=self.core.latest.get(tag.id)
                if not sample or sample.quality!='OK' or self.failures[d.id]: raise RuntimeError('Comunicação indisponível; não enviado')
                # Persist intent before touching the equipment. Never replay on restart.
                self.core.repo.command(identifier,time.time(),tag.id,value,'Enviando')
                result='Indeterminado'
                self.transport.write(d.unit_id,tag.function,tag.address,encoded)
                result='Confirmado'
            except Exception as e: detail=str(e)
            try:
                self.core.repo.command(identifier,time.time(),tag.id,value,result,detail)
            except Exception as e:
                detail += f' Falha no log de comando: {e}'
                log.exception('Falha no log de escrita')
            log.info('Escrita %s tag=%s valor=%s %s %s',identifier,tag.name,value,result,detail)
            future.set_result((result,detail))


def scan(device, function, start, end, cancel, callback):
    """Independent, sequential read-only scanner; acquisition must be stopped."""
    device.validate()
    if end<start or end-start+1>512: raise ValueError('Busca de registradores limitada a 512 endereços por execução')
    validate_range(function,start,1); validate_range(function,end,1)
    transport=make_transport(replace(device,retries=0))
    try:
        for address in range(start,end+1):
            if cancel.is_set(): break
            try: callback(address,transport.read(device.unit_id,function,address,1)[0],'OK')
            except Exception as e: callback(address,None,str(e))
            if cancel.wait(.05): break
    finally: transport.close()
