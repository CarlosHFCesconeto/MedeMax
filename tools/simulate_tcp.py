"""Local-only Modbus TCP simulator. Map is fictitious, documented below."""
import argparse
from pymodbus.server import StartTcpServer
from pymodbus.simulator import SimDevice, SimData, DataType

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=15020); args=parser.parse_args()
    # Unified map: holding/input registers 0..3 = 2203,470,1030,650;
    # remaining words are zero. This is NOT a real instrument profile.
    device=SimDevice(1,[SimData(0,count=1,values=[2203,470,1030,650],datatype=DataType.REGISTERS),SimData(4,count=96,values=0,datatype=DataType.REGISTERS)])
    print(f'Simulador TCP local 127.0.0.1:{args.port}, Unit ID 1',flush=True)
    StartTcpServer(device,address=('127.0.0.1',args.port))
