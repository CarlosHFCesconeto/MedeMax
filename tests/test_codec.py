import struct
import math
import pytest
from app.models import Tag,TYPES
from app.codec import decode,encode


@pytest.mark.parametrize('kind,value', [('UINT16',65535),('INT16',-32768),('UINT32',4294967295),('INT32',-2147483648),('FLOAT32',-123.25),('FLOAT64',123456.789)])
@pytest.mark.parametrize('byte',['big','little'])
@pytest.mark.parametrize('word',['big','little'])
def test_decode_encode_known_bytes(kind,value,byte,word):
    tag=Tag(device_id='d',data_type=kind,count=TYPES[kind][1],byte_order=byte,word_order=word,writable=True)
    raw=struct.pack('>'+TYPES[kind][0],value)
    words=[raw[i:i+2] for i in range(0,len(raw),2)]
    if byte=='little': words=[w[::-1] for w in words]
    if word=='little': words.reverse()
    registers=[int.from_bytes(w,'big') for w in words]
    assert decode(registers,tag)==pytest.approx(value)
    assert encode(value,tag)==registers


def test_scale_offset_and_range():
    tag=Tag(device_id='d',scale=.1,offset=5,writable=True,write_min=0,write_max=300)
    assert decode([2203],tag)==pytest.approx(225.3)
    assert encode(225.3,tag)==[2203]
    for invalid in (301,-1,float('nan'),float('inf'),225.33):
        with pytest.raises(ValueError): encode(invalid,tag)


def test_fixed_byte_order_vectors():
    for byte,word,registers in [('big','big',[0x1234,0x5678]),('little','big',[0x3412,0x7856]),('big','little',[0x5678,0x1234]),('little','little',[0x7856,0x3412])]:
        assert decode(registers,Tag(device_id='d',data_type='UINT32',count=2,byte_order=byte,word_order=word))==0x12345678


def test_bool_and_invalid_config():
    t=Tag(device_id='d',function=1,data_type='Boolean',writable=True)
    assert decode([1],t) is True
    assert encode(0,t)==[False]
    with pytest.raises(ValueError): encode(2,t)
    for tag in [Tag(device_id='d',address=65535,count=2,data_type='FLOAT32'),Tag(device_id='d',function=4,writable=True),Tag(device_id='d',count=3)]:
        with pytest.raises(ValueError): tag.validate()
    with pytest.raises(ValueError): decode([0x7f80,0],Tag(device_id='d',data_type='FLOAT32',count=2))
    with pytest.raises(ValueError): encode(1,Tag(device_id='d'))
