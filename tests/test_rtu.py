"""Linux virtual serial integration; does not replace physical RS485 validation."""
import os
import select
import struct
import threading
import pytest
from app.communication.transports import ClientTransport
from app.models import Device


def crc(data):
    value=0xffff
    for byte in data:
        value^=byte
        for _ in range(8): value=(value>>1)^0xa001 if value&1 else value>>1
    return value.to_bytes(2,'little')


@pytest.mark.skipif(os.name=='nt',reason='PTY disponível somente em POSIX')
def test_rtu_on_virtual_serial():
    import pty
    master,slave=pty.openpty(); port=os.ttyname(slave); stop=threading.Event(); requests=[]
    def server():
        buf=b''
        while not stop.is_set():
            ready,_,_=select.select([master],[],[],.1)
            if not ready: continue
            buf+=os.read(master,1024)
            while len(buf)>=8:
                packet,buf=buf[:8],buf[8:]
                if crc(packet[:-2])!=packet[-2:]: continue
                requests.append(packet)
                count=int.from_bytes(packet[4:6],'big')
                body=bytes([packet[0],packet[1],2*count])+struct.pack('>H',2203)*count if packet[1] in (3,4) else packet[:-2]
                os.write(master,body+crc(body))
    thread=threading.Thread(target=server); thread.start()
    client=ClientTransport(Device(port=port,timeout=.3,retries=0))
    try:
        assert client.read(1,3,0,1)==[2203]
        assert client.read(1,4,0,26)==[2203]*26
        assert requests[-1][1:6]==bytes([4,0,0,0,26])
        client.write(1,3,0,[100]); assert len(requests)==3
    finally:
        client.close();stop.set();thread.join(2);os.close(master);os.close(slave)
