"""Senha no Cofre de Credenciais do Windows, sem arquivo ou log de senha."""
import ctypes
from ctypes import wintypes

TARGET='DashboardGerencial/CPS/DevLeitura'

class Credential(ctypes.Structure):
    _fields_=[('Flags',wintypes.DWORD),('Type',wintypes.DWORD),('TargetName',wintypes.LPWSTR),
              ('Comment',wintypes.LPWSTR),('LastWritten',wintypes.FILETIME),('CredentialBlobSize',wintypes.DWORD),
              ('CredentialBlob',ctypes.POINTER(ctypes.c_ubyte)),('Persist',wintypes.DWORD),
              ('AttributeCount',wintypes.DWORD),('Attributes',ctypes.c_void_p),('TargetAlias',wintypes.LPWSTR),('UserName',wintypes.LPWSTR)]

def api():
    a=ctypes.WinDLL('Advapi32.dll',use_last_error=True)
    a.CredWriteW.argtypes=[ctypes.POINTER(Credential),wintypes.DWORD];a.CredWriteW.restype=wintypes.BOOL
    a.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(Credential))];a.CredReadW.restype=wintypes.BOOL
    a.CredFree.argtypes=[ctypes.c_void_p]
    return a

def salvar_senha(senha):
    a=api();data=senha.encode('utf-16-le');buffer=(ctypes.c_ubyte*len(data)).from_buffer_copy(data)
    c=Credential(Type=1,TargetName=TARGET,CredentialBlobSize=len(data),CredentialBlob=buffer,Persist=2,UserName='DevLeitura')
    if not a.CredWriteW(ctypes.byref(c),0):raise OSError('Nao foi possivel guardar credencial no cofre Windows')

def ler_senha():
    a=api();ptr=ctypes.POINTER(Credential)()
    if not a.CredReadW(TARGET,1,0,ctypes.byref(ptr)):raise RuntimeError('Configure DB_PASSWORD ou a credencial CPS no cofre Windows')
    try:return ctypes.string_at(ptr.contents.CredentialBlob,ptr.contents.CredentialBlobSize).decode('utf-16-le')
    finally:a.CredFree(ptr)
