# -*- coding:UTF-8 -*-

import base64
from Crypto.Cipher import AES
# ��Կ��key��, ��˹ƫ������iv�� CBCģʽ����
 
def AES_Encrypt(key, data):
    vi = '0102030405060708'
    pad = lambda s: s + (16 - len(s)%16) * chr(16 - len(s)%16)
    data = pad(data)
    # �ַ�����λ
    cipher = AES.new(key.encode('utf8'), AES.MODE_CBC, vi.encode('utf8'))
    encryptedbytes = cipher.encrypt(data.encode('utf8'))
    # ���ܺ�õ�����bytes���͵�����
    encodestrs = base64.b64encode(encryptedbytes)
    # ʹ��Base64���б���,����byte�ַ���
    enctext = encodestrs.decode('utf8')
    # ��byte�ַ�����utf-8���н���
    return enctext
 
 
def AES_Decrypt(key, data):
    vi = '0102030405060708'
    data = data.encode('utf8')
    encodebytes = base64.decodebytes(data)
    # ����������ת��λbytes��������
    cipher = AES.new(key.encode('utf8'), AES.MODE_CBC, vi.encode('utf8'))
    text_decrypted = cipher.decrypt(encodebytes)
    unpad = lambda s: s[0:-s[-1]]
    text_decrypted = unpad(text_decrypted)
    # ȥ��λ
    text_decrypted = text_decrypted.decode('utf8')
    return text_decrypted
 
 
key = '0CoJUm6Qyw8W8jud'
data = 'sdadsdsdsfd'
AES_Encrypt(key, data)
enctext = AES_Encrypt(key, data)
print(enctext)
text_decrypted = AES_Decrypt(key, enctext)
print(text_decrypted)
 
#hBXLrMkpkBpDFsf9xSRGQQ==sdadsdsdsfd