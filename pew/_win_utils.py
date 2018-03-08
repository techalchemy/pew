# -*- coding=utf-8 -*-
# psutil is painfully slow in win32. So to avoid adding big
# dependencies like pywin32 a ctypes based solution is preferred

# Code based on the winappdbg project http://winappdbg.sourceforge.net/
# (BSD License) - adapted from Celery
# https://github.com/celery/celery/blob/2.5-archived/celery/concurrency/processes/_win.py
import os
from ctypes import (
    byref, sizeof, windll, Structure, WinError, POINTER,
    c_size_t, c_char, c_void_p
)
from ctypes.wintypes import DWORD, LONG

ERROR_NO_MORE_FILES = 18
INVALID_HANDLE_VALUE = c_void_p(-1).value


class PROCESSENTRY32(Structure):
    _fields_ = [
        ('dwSize', DWORD),
        ('cntUsage', DWORD),
        ('th32ProcessID', DWORD),
        ('th32DefaultHeapID', c_size_t),
        ('th32ModuleID', DWORD),
        ('cntThreads', DWORD),
        ('th32ParentProcessID', DWORD),
        ('pcPriClassBase', LONG),
        ('dwFlags', DWORD),
        ('szExeFile', c_char * 260),
    ]


LPPROCESSENTRY32 = POINTER(PROCESSENTRY32)


def CreateToolhelp32Snapshot(dwFlags=2, th32ProcessID=0):
    hSnapshot = windll.kernel32.CreateToolhelp32Snapshot(
        dwFlags,
        th32ProcessID
    )
    if hSnapshot == INVALID_HANDLE_VALUE:
        raise WinError()
    return hSnapshot


def Process32First(hSnapshot):
    pe = PROCESSENTRY32()
    pe.dwSize = sizeof(PROCESSENTRY32)
    success = windll.kernel32.Process32First(hSnapshot, byref(pe))
    if not success:
        if windll.kernel32.GetLastError() == ERROR_NO_MORE_FILES:
            return
        raise WinError()
    return pe


def Process32Next(hSnapshot, pe=None):
    if pe is None:
        pe = PROCESSENTRY32()
    pe.dwSize = sizeof(PROCESSENTRY32)
    success = windll.kernel32.Process32Next(hSnapshot, byref(pe))
    if not success:
        if windll.kernel32.GetLastError() == ERROR_NO_MORE_FILES:
            return
        raise WinError()
    return pe


def get_all_processes():
    """Return a dictionary of properties about all processes.

    >>> get_all_processes()
    {
        1509: {
            'parent_pid': 1201,
            'executable': 'C:\\Program\\\\ Files\\Python36\\python.exe'
        }
    }
    """
    h_process = CreateToolhelp32Snapshot()
    pids = {}
    pe = Process32First(h_process)
    while pe:
        pids[pe.th32ProcessID] = {
            'executable': str(pe.szExeFile.decode('utf-8')),
        }
        if pe.th32ParentProcessID:
            pids[pe.th32ProcessID]['parent_pid'] = pe.th32ParentProcessID
        pe = Process32Next(h_process, pe)

    return pids


def get_grandparent_process(pid=None):
    """Get grandparent process name of the supplied pid or os.getpid().

    :param int pid: The pid to track.
    :return: Name of the grandparent process.
    """
    if not pid:
        pid = os.getpid()
    processes = get_all_processes()
    ppid = processes[pid]['parent_pid']
    parent = processes[ppid]
    grandparent = processes[parent['parent_pid']]
    return grandparent['executable']
