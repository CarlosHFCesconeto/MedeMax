import socket
import struct
import threading
import time
import pytest
from app.communication.transports import ClientTransport
from app.models import Device


def test_no_retry_when_write_ack_is_lost():
    listener=socket.socket(); listener.bind(('127.0.0.1',0)); listener.listen(); listener.settimeout(3)
    frames=[]
    def server():
        conn,_=listener.accept(); conn.settimeout(.5)
        with conn:
            while True:
                try: data=conn.recv(1024)
                except socket.timeout: break
                if not data: break
                frames.append(data)
                # Deliberately no reply. Client must not repeat a write.
    worker=threading.Thread(target=server); worker.start()
    client=ClientTransport(Device(transport='TCP',tcp_port=listener.getsockname()[1],timeout=.1,retries=3))
    try:
        client.connect()
        with pytest.raises(Exception): client.write(1,3,0,[100])
        assert client.client.transaction.retries==3
    finally:
        client.close(); worker.join(3); listener.close()
    assert len(frames)==1 and frames[0][7]==6


def test_write_does_not_establish_connection():
    client=ClientTransport(Device(transport='TCP',tcp_port=1,timeout=.1))
    with pytest.raises(ConnectionError): client.write(1,3,0,[1])
    assert client.client is None
