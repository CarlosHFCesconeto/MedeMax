import subprocess
import sys
from app.session import SessionLock


def test_second_process_cannot_share_data_directory(tmp_path):
    path=tmp_path/'lock'; lock=SessionLock(path)
    code='from app.session import SessionLock; import sys; SessionLock(sys.argv[1]).close()'
    try:
        result=subprocess.run([sys.executable,'-c',code,str(path)],capture_output=True)
        assert result.returncode!=0 and b'RuntimeError' in result.stderr
    finally: lock.close()
    result=subprocess.run([sys.executable,'-c',code,str(path)],capture_output=True)
    assert result.returncode==0
