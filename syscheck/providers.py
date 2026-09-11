"""Провайдеры данных — собирают метрики, не печатают.

Отделены от рендера, чтобы одни и те же данные можно было показывать
в CLI-выводе, в TUI-панели и в JSON.
"""
from __future__ import annotations

import os
import platform
import re
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from collections import namedtuple
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import psutil


# --- CPU: неблокирующий расчёт дельт по собственным выборкам -------------
_cpu_prev: Optional[Tuple[float, Any, Any]] = None


# --- короткая история для спарклайнов ------------------------------------
_cpu_hist: deque = deque(maxlen=60)
_net_down_hist: deque = deque(maxlen=60)
_net_up_hist: deque = deque(maxlen=60)
_disk_read_hist: deque = deque(maxlen=60)
_disk_write_hist: deque = deque(maxlen=60)


def cpu_history() -> List[float]:
    return list(_cpu_hist)


def net_history() -> Dict[str, List[float]]:
    return {"down": list(_net_down_hist), "up": list(_net_up_hist)}


def disk_history() -> Dict[str, List[float]]:
    return {"read": list(_disk_read_hist), "write": list(_disk_write_hist)}


def _cpu_percent_from_times(a, b) -> float:
    """Процент занятости CPU из двух выборок cpu_times() одного ядра."""
    idle_d = max(b.idle - a.idle, 0)
    total_d = max(sum(b) - sum(a), idle_d)
    if total_d <= 0:
        return 0.0
    return max(0.0, min(100.0, (total_d - idle_d) / total_d * 100.0))


def cpu_delta() -> Optional[Tuple[float, List[float]]]:
    """Неблокирующий (overall %, per-core %).

    Считает прирост по сырым счётчикам cpu_times() с прошлого вызова —
    без блокирующего interval и без сна. Первый вызов возвращает None
    (нет базовой выборки).
    """
    global _cpu_prev
    now = time.time()
    overall = psutil.cpu_times()
    per = psutil.cpu_times(percpu=True)
    if _cpu_prev is None:
        _cpu_prev = (now, overall, per)
        return None
    t0, o0, p0 = _cpu_prev
    _cpu_prev = (now, overall, per)
    dt = now - t0
    if dt <= 0.05:
        return None
    overall_pct = _cpu_percent_from_times(o0, overall)
    _cpu_hist.append(overall_pct)
    return overall_pct, [
        _cpu_percent_from_times(x0, x) for x0, x in zip(p0, per)
    ]


def cpu_info(interval: float = 0.3) -> Dict[str, Any]:
    freq = psutil.cpu_freq()
    return {
        "percent": psutil.cpu_percent(interval=interval),
        "count_logical": psutil.cpu_count(logical=True),
        "count_physical": psutil.cpu_count(logical=False),
        "freq_current": freq.current if freq else None,
        "freq_max": freq.max if freq else None,
        "per_cpu": psutil.cpu_percent(interval=0, percpu=True),
    }


def ram_info(top: bool = True) -> Dict[str, Any]:
    mem = psutil.virtual_memory()
    swap = _swap_slow()
    procs = []
    if top:
        for p in psutil.process_iter(["pid", "name", "memory_percent"]):
            try:
                pinfo = p.info
                if pinfo["memory_percent"] and pinfo["memory_percent"] > 0.1:
                    procs.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: x["memory_percent"] or 0, reverse=True)
    return {
        "total": mem.total,
        "available": mem.available,
        "used": mem.used,
        "cached": getattr(mem, "cached", 0) or 0,
        "percent": mem.percent,
        "swap_total": swap.total,
        "swap_used": swap.used,
        "swap_percent": swap.percent,
        "top_procs": procs[:10],
    }


_swap_cache: dict = {"ts": 0.0, "v": None}
_SWAP_TTL = 5.0


def _swap_slow():
    """psutil.swap_memory() на Windows может занимать ~600 мс — кэшируем."""
    now = time.time()
    v = _swap_cache["v"]
    if v is None or now - _swap_cache["ts"] > _SWAP_TTL:
        _swap_cache["v"] = psutil.swap_memory()
        _swap_cache["ts"] = now
    return _swap_cache["v"]


def disk_info() -> Dict[str, Any]:
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            })
        except (PermissionError, OSError):
            pass
    io = None
    try:
        io = psutil.disk_io_counters()
    except Exception:
        pass
    return {"disks": disks, "io": io}


def net_info() -> Dict[str, Any]:
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    interfaces = []
    for name, iface_addrs in addrs.items():
        stat = stats.get(name)
        ipv4 = [a.address for a in iface_addrs if a.family == socket.AF_INET]
        mac_list = [a.address for a in iface_addrs if a.family == psutil.AF_LINK]
        interfaces.append({
            "name": name,
            "up": bool(stat and stat.isup),
            "speed": stat.speed if stat else 0,
            "ipv4": ipv4,
            "mac": mac_list[:1] or [],
        })
    try:
        io = psutil.net_io_counters()
        io_data = {
            "bytes_sent": io.bytes_sent,
            "bytes_recv": io.bytes_recv,
            "packets_sent": io.packets_sent,
            "packets_recv": io.packets_recv,
            "errin": io.errin,
            "errout": io.errout,
        }
    except Exception:
        io_data = None
    return {"interfaces": interfaces, "io": io_data}


def _decode_ping_output(raw: bytes) -> str:
    for enc in ("cp866", "cp1251", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1", errors="replace")


def ping(host: str, count: int = 4) -> Dict[str, Any]:
    """Пингует хост и возвращает статистику."""
    param = "-n" if sys.platform == "win32" else "-c"
    try:
        result = subprocess.run(
            ["ping", param, str(count), host],
            capture_output=True, timeout=15,
        )
        output = _decode_ping_output(result.stdout)
        pattern = re.compile(r"=\s*(\d+)\s*(?:\u043c\u0441|ms)", re.IGNORECASE)
        matches = list(pattern.finditer(output))
        times = []
        for m in matches[:count]:
            ctx = output[m.end():m.end() + 20]
            if "TTL" in ctx or not re.search(r"\d+\s*(?:\u043c\u0441|ms)", ctx):
                try:
                    times.append(float(m.group(1)))
                except (ValueError, TypeError):
                    pass
        avg = sum(times) / len(times) if times else None
        return {
            "host": host,
            "success": result.returncode == 0,
            "avg_ms": avg,
            "min_ms": min(times) if times else None,
            "max_ms": max(times) if times else None,
            "lost": max(0, count - len(times)),
            "total": count,
        }
    except (subprocess.TimeoutExpired, Exception) as e:
        return {
            "host": host,
            "success": False,
            "error": str(e),
            "avg_ms": None,
            "lost": count,
            "total": count,
        }


# --- процессы: кэш объектов + неблокирующие дельты CPU ------------------
_proc_objs: List[Any] = []
_proc_list_time: float = 0.0
_proc_samples: Dict[int, Tuple[float, float, float]] = {}
_proc_raw: List[Dict[str, Any]] = []
_proc_raw_time: float = 0.0
_proc_lock = threading.Lock()
_PROC_REFRESH_EVERY = 8.0
_PROC_CPU_EVERY = 3.0


def _refresh_proc_list() -> None:
    """Пересобирает список процессов не чаще раза в _PROC_REFRESH_EVERY сек."""
    global _proc_objs, _proc_list_time
    if time.time() - _proc_list_time < _PROC_REFRESH_EVERY:
        return
    with _proc_lock:
        if time.time() - _proc_list_time < _PROC_REFRESH_EVERY:
            return
        listed = []
        for p in psutil.process_iter(["pid", "name", "memory_percent", "status", "memory_info"]):
            try:
                # на Windows pid 0 — «System Idle Process», его cpu% равен общему
                # простою всех ядер (может быть >1000%) и вводит в заблуждение.
                if p.info["pid"] == 0:
                    continue
                listed.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        _proc_objs = listed
        _proc_list_time = time.time()
        live = {p.pid for p in listed}
        for pid in [k for k in _proc_samples if k not in live]:
            _proc_samples.pop(pid, None)


def _process_cpu_delta(p) -> float:
    """CPU% процесса по приросту cpu_times() между вызовами (без блокировок)."""
    try:
        t = p.cpu_times()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0
    now = time.time()
    pid = p.pid
    prev = _proc_samples.get(pid)
    _proc_samples[pid] = (now, t.user, t.system)
    if prev is None:
        return 0.0
    dt = now - prev[0]
    if dt <= 0.05:
        return 0.0
    du = max((t.user - prev[1]) + (t.system - prev[2]), 0.0)
    return du / dt * 100.0


def _refresh_proc_raw() -> List[Dict[str, Any]]:
    """Сырые данные процессов (с CPU-дельтой). Пересчёт CPU не чаще _PROC_CPU_EVERY."""
    global _proc_raw, _proc_raw_time
    now = time.time()
    if now - _proc_raw_time < _PROC_CPU_EVERY and _proc_raw:
        return _proc_raw
    _refresh_proc_list()
    raw = []
    for p in _proc_objs:
        try:
            info = p.info  # имя/pid/status кэшированы при сборке списка
            info["cpu_percent"] = _process_cpu_delta(p)
            mi = info.get("memory_info")
            info["rss"] = getattr(mi, "rss", 0) if mi else 0
            raw.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _proc_raw = raw
    _proc_raw_time = now
    return raw


def processes(sort_by: str = "cpu", limit: int = 15) -> List[Dict[str, Any]]:
    data = list(_refresh_proc_raw())
    key = {"cpu": "cpu_percent", "ram": "memory_percent", "name": "name"}.get(
        sort_by, "cpu_percent"
    )
    if key == "name":
        data.sort(key=lambda x: x.get(key, "") or "")
    else:
        data.sort(key=lambda x: x.get(key, 0) or 0, reverse=True)
    return data[:limit]


def temperatures() -> Dict[str, Any]:
    """Температуры: psutil, при пустоте на Windows — ACPI-зоны через WMI.

    Возвращает {"available","temps","source"}; каждая запись совместима
    с psutil.shwtemp (current/high/critical/label).
    """
    if hasattr(psutil, "sensors_temperatures"):
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                return {"available": True, "temps": temps, "source": "psutil"}
        except (AttributeError, Exception):
            pass
    if sys.platform == "win32":
        wmi_temps = _windows_acpi_temps()
        if wmi_temps is not None:
            return {"available": bool(wmi_temps), "temps": wmi_temps, "source": "wmi"}
    return {"available": False, "temps": {}, "source": None}


_ShwTemp = namedtuple("ShwTemp", ("current", "high", "critical", "label"))


def _windows_acpi_temps() -> Optional[Dict[str, List[Any]]]:
    """ACPI-термозоны Windows: MSAcpi_ThermalZoneTemperature (долго ≠ точно).

    Значение в децикельвинах, грубое (часто «застрявшая» константа на
    многих ноутбуках), но это единственное, что отдаёт Windows без
    чужого кода. None, если WMI недоступен/пуст.
    """
    try:
        out = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature |"
                " Select-Object -ExpandProperty CurrentTemperature",
            ],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (subprocess.TimeoutExpired, OSError, Exception):
        return None
    raw = (out.stdout or "").strip()
    if out.returncode != 0 or not raw:
        return None
    entries = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or not re.fullmatch(r"\d+(\.\d+)?", line):
            continue
        try:
            celsius = round(float(line) / 10.0 - 273.15, 1)
        except (ValueError, TypeError):
            continue
        entries.append(_ShwTemp(celsius, None, None, "ACPI zone"))
    if not entries:
        return None
    return {"acpi": entries}


def system_info() -> Dict[str, Any]:
    uname = platform.uname()
    boot = psutil.boot_time()
    users = []
    try:
        users = sorted(set(u.name for u in psutil.users()))
    except Exception:
        pass
    return {
        "os": f"{uname.system} {uname.release}",
        "version": uname.version,
        "machine": uname.machine,
        "node": uname.node,
        "processor": uname.processor or "N/A",
        "python": platform.python_version(),
        "boot_time": boot,
        "uptime_seconds": time.time() - boot,
        "boot_datetime": datetime.fromtimestamp(boot).strftime("%Y-%m-%d %H:%M:%S"),
        "users": users,
    }


def system_quick() -> Dict[str, Any]:
    data = {"cpu_percent": psutil.cpu_percent(interval=0.3)}
    mem = psutil.virtual_memory()
    data["ram_percent"] = mem.percent
    data["ram_available"] = mem.available
    data["disks"] = []
    for d in disk_info()["disks"]:
        data["disks"].append((d["device"], d["percent"], d["free"]))
    if psutil.disk_usage("C:\\" if os.name == "nt" else "/"):
        try:
            root = psutil.disk_usage("C:\\" if os.name == "nt" else "/")
            data["main_percent"], data["main_free"] = root.percent, root.free
        except Exception:
            pass
    try:
        io = psutil.net_io_counters()
        data["net_sent"] = io.bytes_sent
        data["net_recv"] = io.bytes_recv
    except Exception:
        pass
    return data


# --- дисковые скорости чтения/записи (MB/s по дельтам) ----------------
_io_prev: Optional[Tuple[float, int, int]] = None


def disk_io_speeds() -> Dict[str, float]:
    """Скорости диска за интервал между вызовами (bytes/s). Неблокирующе."""
    global _io_prev
    try:
        io = psutil.disk_io_counters()
    except Exception:
        return {"read": 0.0, "write": 0.0}
    now = time.time()
    if _io_prev is None:
        _io_prev = (now, io.read_bytes, io.write_bytes)
        return {"read": 0.0, "write": 0.0}
    t0, r0, w0 = _io_prev
    _io_prev = (now, io.read_bytes, io.write_bytes)
    dt = max(now - t0, 1e-6)
    read_speed = max(io.read_bytes - r0, 0) / dt
    write_speed = max(io.write_bytes - w0, 0) / dt
    _disk_read_hist.append(read_speed)
    _disk_write_hist.append(write_speed)
    return {
        "read": read_speed,
        "write": write_speed,
    }


# --- GPU (best-effort, кэш) -------------------------------------------
_gpu_cache: dict = {"ts": 0.0, "data": None}
_GPU_TTL = 30.0


def gpu_info() -> Dict[str, Any]:
    """Данные видеокарты: nvidia-smi, иначе WMI (имя/VRAM).

    Возвращает {"name","vram_gb","vram_used_gb","util","temp","source"};
    недоступные поля — None. «Честно»: если драйвер не отдаёт загрузку
    или температуру, поля остаются None, а не 0.
    """
    now = time.time()
    if _gpu_cache["data"] is not None and now - _gpu_cache["ts"] < _GPU_TTL:
        return _gpu_cache["data"]
    data: Dict[str, Any] = {
        "name": None, "vram_gb": None, "vram_used_gb": None,
        "util": None, "temp": None, "source": None,
    }
    nv = _nvidia_smi_info()
    if nv:
        data.update(nv)
    else:
        data.update(_wmi_gpu_info())
    if not data["name"]:
        data["name"], data["vram_gb"] = _wmic_gpu_name_vram()
    _gpu_cache["data"], _gpu_cache["ts"] = data, now
    return data


def _nvidia_smi_info() -> Optional[Dict[str, Any]]:
    """nvidia-smi (NVIDIA): имя, util, temp, VRAM used/total. None — нет nvidia."""
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (subprocess.TimeoutExpired, OSError, Exception):
        return None
    lines = (out.stdout or "").strip().splitlines()
    if out.returncode != 0 or not lines:
        return None
    parts = [p.strip() for p in lines[0].split(",")]
    if len(parts) < 5 or not parts[0]:
        return None

    def _opt(val: str, div: float = 1.0) -> Optional[float]:
        if "N/A" in val.lower():
            return None
        try:
            return round(float(val) / div, 1)
        except (ValueError, TypeError):
            return None

    return {
        "name": parts[0],
        "util": _opt(parts[1]),
        "temp": _opt(parts[2]),
        "vram_used_gb": _opt(parts[3], 1024.0),
        "vram_gb": _opt(parts[4], 1024.0),
        "source": "nvidia-smi",
    }


def _wmi_gpu_info() -> Dict[str, Any]:
    """Best-effort имя + VRAM через PowerShell WMI (AMD/Intel/NVIDIA без nvidia-smi)."""
    data: Dict[str, Any] = {
        "name": None, "vram_gb": None, "vram_used_gb": None,
        "util": None, "temp": None, "source": "wmi",
    }
    try:
        out = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_VideoController | Where-Object { $_.Name -notlike '*Virtual*' } |"
                " Select-Object -First 1 -Property Name,AdapterRAM | ConvertTo-Json -Compress",
            ],
            capture_output=True, text=True, timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        raw = out.stdout.strip()
        if raw:
            import json as _json
            info = _json.loads(raw)
            vram = info.get("AdapterRAM")
            if vram:
                vram = float(vram) / (1024 ** 3)
            data["name"] = info.get("Name") or data["name"]
            data["vram_gb"] = round(vram, 1) if vram else None
    except Exception:
        pass
    return data


def _wmic_gpu_name_vram() -> Tuple[Optional[str], Optional[float]]:
    """Старый путь wmic, если PowerShell не отдал имя."""
    name, vram = None, None
    try:
        out = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "name"],
            capture_output=True, text=True, timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        lines = [ln.strip() for ln in out.stdout.splitlines()
                 if ln.strip() and ln.strip().lower() != "name"]
        lines = [ln for ln in lines if "virtual" not in ln.lower()]
        name = lines[0] if lines else None
    except Exception:
        pass
    return name, vram


def process_count() -> int:
    """Количество процессов из кэша (после пересборки списка)."""
    _refresh_proc_list()
    return len(_proc_objs)


def cpu_temp_celsius() -> Optional[float]:
    """Температура CPU, если psutil её видит на данной ОС."""
    try:
        for entries in psutil.sensors_temperatures().values():
            if entries:
                return entries[0].current
    except (AttributeError, Exception):
        return None
    return None

# --- CPU: детальная карточка -------------------------------------------
def cpu_detail() -> Dict[str, Any]:
    """CPU с моделью и температурой — для команды/панели cpu."""
    d = dict(cpu_info(interval=0.25))
    d["model"] = platform.processor() or "N/A"
    d["temp"] = cpu_temp_celsius()
    return d


# --- батарея ------------------------------------------------------------
def battery_info() -> Optional[Dict[str, Any]]:
    """Данные батареи или None, если в системе нет батареи."""
    try:
        b = psutil.sensors_battery()
        if b is None:
            return None
        secs = b.secsleft
        left = None
        if secs not in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN) and secs > 0:
            left = int(secs)
        return {"percent": b.percent, "plugged": bool(b.power_plugged), "seconds_left": left}
    except (AttributeError, Exception):
        return None


# --- сеть: скорости по дельтам ------------------------------------------
_net_prev: Optional[Tuple[float, int, int]] = None


def network_speeds() -> Dict[str, float]:
    """Текущие скорости сети (bytes/s) по дельтам счётчиков."""
    global _net_prev
    try:
        io = psutil.net_io_counters()
    except Exception:
        return {"down": 0.0, "up": 0.0}
    now = time.time()
    if _net_prev is None:
        _net_prev = (now, io.bytes_recv, io.bytes_sent)
        return {"down": 0.0, "up": 0.0}
    t0, r0, s0 = _net_prev
    _net_prev = (now, io.bytes_recv, io.bytes_sent)
    dt = max(now - t0, 1e-6)
    down_speed = max(io.bytes_recv - r0, 0) / dt
    up_speed = max(io.bytes_sent - s0, 0) / dt
    _net_down_hist.append(down_speed)
    _net_up_hist.append(up_speed)
    return {
        "down": down_speed,
        "up": up_speed,
    }


# --- сеть: соединения по процессам (кэш) --------------------------------
_conn_cache: dict = {"ts": 0.0, "data": None}
_CONN_TTL = 4.0


def connections_by_process(top_n: int = 10, kind: str = "tcp") -> Dict[str, Any]:
    """TCP-соединения, сгруппированные по процессам (имя -> число)."""
    now = time.time()
    if _conn_cache["data"] is not None and now - _conn_cache["ts"] < _CONN_TTL:
        return _conn_cache["data"]
    _refresh_proc_list()
    pid2name = {(p.info.get("pid")): (p.info.get("name") or "?") for p in _proc_objs}
    counts: Dict[str, int] = {}
    total = 0
    try:
        conns = psutil.net_connections(kind=kind)
    except (psutil.AccessDenied, psutil.PermissionError):
        conns = []
    except Exception:
        conns = []
    for c in conns:
        total += 1
        if c.pid in (0, 4):
            name = "system"
        else:
            name = pid2name.get(c.pid) if c.pid is not None else None
        if name is None:
            name = "kernel" if c.pid is None else f"?({c.pid})"
        counts[name] = counts.get(name, 0) + 1
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    data = {"total": total, "top": top}
    _conn_cache["data"], _conn_cache["ts"] = data, now
    return data


# --- процессы: детали и управление --------------------------------------
def _window_handle_count(pid: int) -> Optional[int]:
    """Число открытых хэндлов (Windows) или None."""
    if sys.platform != "win32":
        return None
    try:
        from ctypes import byref, c_ulong, windll
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return None
        try:
            cnt = c_ulong()
            if windll.kernel32.GetProcessHandleCount(h, byref(cnt)):
                return int(cnt.value)
            return None
        finally:
            windll.kernel32.CloseHandle(h)
    except Exception:
        return None


def process_detail(pid: int) -> Optional[Dict[str, Any]]:
    """Расширенная карточка процесса или None, если процесс исчез."""
    try:
        p = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return None
    info: Dict[str, Any] = {
        "pid": pid,
        "name": "?", "cpu": 0.0, "memory_percent": 0.0, "rss": 0,
        "threads": None, "status": "?", "cmdline": [], "exe": None,
        "handles": None, "create_time": None, "uptime_seconds": 0.0,
    }
    try:
        info["name"] = p.name() or "?"
    except (psutil.AccessDenied, Exception):
        pass
    try:
        info["cpu"] = _process_cpu_delta(p)
    except Exception:
        pass
    try:
        info["memory_percent"] = p.memory_percent()
    except (psutil.AccessDenied, Exception):
        pass
    try:
        info["rss"] = p.memory_info().rss
    except (psutil.AccessDenied, Exception):
        pass
    try:
        info["threads"] = p.num_threads()
    except (psutil.AccessDenied, Exception):
        pass
    try:
        info["status"] = p.status()
    except (psutil.AccessDenied, Exception):
        pass
    try:
        info["cmdline"] = list(p.cmdline() or [])
    except (psutil.AccessDenied, Exception):
        pass
    try:
        info["exe"] = p.exe()
    except (psutil.AccessDenied, Exception):
        pass
    try:
        info["handles"] = _window_handle_count(pid)
    except Exception:
        pass
    try:
        info["create_time"] = p.create_time()
        info["uptime_seconds"] = max(time.time() - info["create_time"], 0)
    except (psutil.AccessDenied, Exception):
        pass
    return info


def find_process(query: str) -> Optional[Dict[str, Any]]:
    """Ищет процесс по pid или подстроке имени."""
    _refresh_proc_list()
    q = query.strip().lower()
    if q.isdigit():
        pid = int(q)
        for p in _proc_objs:
            if p.info["pid"] == pid:
                return _proc_detail_from_cache(p)
        return None
    for p in _proc_objs:
        nm = p.info.get("name") or ""
        if nm.lower().find(q) != -1:
            return _proc_detail_from_cache(p)
    return None


def _proc_detail_from_cache(p) -> Dict[str, Any]:
    return {
        "pid": p.info.get("pid"), "name": p.info.get("name") or "?",
        "cpu": p.info.get("cpu_percent") or 0.0,
        "memory_percent": p.info.get("memory_percent") or 0.0,
    }


def list_processes(query: Optional[str] = None, sort: str = "cpu",
                   limit: int = 25) -> List[Dict[str, Any]]:
    """Список процессов (имя+pid+лог), с фильтром и сортировкой."""
    data = [dict(p) for p in _refresh_proc_raw()]
    if query:
        q = query.lower()
        data = [d for d in data if q in (d.get("name") or "").lower()
                or q in " ".join([str(d.get("pid"))])]
    key = {"cpu": "cpu_percent", "ram": "memory_percent", "name": "name"}.get(sort, "cpu_percent")
    if key == "name":
        data.sort(key=lambda x: (x.get(key) or "") or "")
    else:
        data.sort(key=lambda x: x.get(key, 0) or 0, reverse=True)
    return data[:limit]


def resolve_pid(query: str) -> Optional[int]:
    """Возвращает pid по числу или подстроке имени."""
    p = find_process(query)
    return p["pid"] if p else None


def kill_process(pid: int) -> str:
    """Завершает процесс; отказывает для собственного pid."""
    if pid == os.getpid():
        raise ValueError("refusing to kill self")
    try:
        p = psutil.Process(pid)
    except psutil.NoSuchProcess:
        raise ValueError(f"no such process: {pid}")
    p.terminate()
    try:
        p.wait(timeout=5)
    except psutil.TimeoutExpired:
        p.kill()
        p.wait(timeout=3)
    return "killed"


def suspend_process(pid: int) -> str:
    if pid == os.getpid():
        raise ValueError("refusing to suspend self")
    psutil.Process(pid).suspend()
    return "suspended"


def resume_process(pid: int) -> str:
    psutil.Process(pid).resume()
    return "resumed"


def restart_process(pid: int) -> str:
    """Перезапуск: завершить и поднять exe заново (best-effort)."""
    if pid == os.getpid():
        raise ValueError("refusing to restart self")
    pid = int(pid)
    exe = None
    try:
        exe = psutil.Process(pid).exe()
    except (psutil.AccessDenied, psutil.NoSuchProcess, Exception):
        pass
    kill_process(pid)
    if exe and os.path.isfile(exe):
        cwd = os.path.dirname(exe) or None
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            subprocess.Popen([exe], cwd=cwd, close_fds=True, creationflags=flags)
            return f"restarted ({exe})"
        except OSError:
            return f"killed, failed to relaunch ({exe})"
    return "killed, nothing to relaunch"
