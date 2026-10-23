"""Cross-platform process lock shared by desktop and headless entry points."""
import os


class SessionLock:
    def __init__(self,path):
        self.file=open(path,'a+b')
        self.file.seek(0,2)
        if self.file.tell()==0: self.file.write(b'0');self.file.flush()
        self.file.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as e:
            self.file.close()
            raise RuntimeError('Outro processo MonitorModbus já usa este diretório de dados.') from e

    def close(self):
        if self.file.closed: return
        if os.name=='nt':
            import msvcrt
            self.file.seek(0); msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(self.file,fcntl.LOCK_UN)
        self.file.close()
