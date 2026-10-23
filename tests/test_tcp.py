import socket
import subprocess
import sys
import time
from pathlib import Path
import pytest
from app.models import Device
from app.communication.transports import ClientTransport,ModbusError


@pytest.fixture
def tcp_server():
    sock=socket.socket(); sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]; sock.close()
    process=subprocess.Popen([sys.executable,str(Path(__file__).parents[1]/'tools/simulate_tcp.py'),'--port',str(port)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        try:
            s=socket.create_connection(('127.0.0.1',port),.1);s.close();break
        except OSError: time.sleep(.05)
    else:
        process.terminate(); out,err=process.communicate(timeout=3); pytest.fail((out+err).decode())
    yield port
    process.terminate(); process.communicate(timeout=5)


def test_real_tcp_read_write_frames(tcp_server):
    frames=[]; client=ClientTransport(Device(transport='TCP',tcp_port=tcp_server),lambda *x:frames.append(x))
    try:
        assert client.read(1,3,0,4)==[2203,470,1030,650]
        assert client.read(1,4,0,1)==[2203]
        client.write(1,3,0,[1234]); assert client.read(1,3,0,1)==[1234]
        client.write(1,3,0,[12,34]); assert client.read(1,3,0,2)==[12,34]
        client.write(1,1,64,[True]); assert client.read(1,1,64,1)==[True]
        assert len(client.read(1,2,64,1))==1
        with pytest.raises(ModbusError): client.read(1,3,200,1)
        assert any(d=='TX' for d,_ in frames) and any(d=='RX' for d,_ in frames)
    finally: client.close()


def test_input26_acquisition_over_real_tcp(tcp_server,tmp_path):
    from app.storage import Repository
    from app.services.core import Core
    values=[22035,22100,21990,525,610,700,40]+[6000]*7+[95,96,97]+[1000,1100,1200,250,200,100]+[1100,1200,1300]
    device=Device(transport='TCP',tcp_port=tcp_server,interval_ms=60000)
    client=ClientTransport(device)
    try:
        client.read(1,3,0,1)
        client.write(1,3,0,values)
    finally: client.close()
    repo=Repository(tmp_path/'db'); core=Core(repo); core.save(device); core.apply_measurement_map(device.id)
    core.trace_enabled=True; core.start()
    try:
        deadline=time.monotonic()+3
        while len(core.latest)<26 and time.monotonic()<deadline: time.sleep(.01)
        assert len(core.latest)==26 and all(s.quality=='OK' for s in core.latest.values())
        assert next(core.latest[t.id].value for t in core.tags.values() if t.address==0)==pytest.approx(220.35)
        operations=[row[3] for row in core.diagnostics if row[2]=='OP']
        assert len(operations)==1 and 'FC04 @0 n=26' in operations[0]
    finally: assert core.stop(); repo.close()
