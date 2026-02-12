# src/utils/helpers.py

import platform
import cpuinfo
import subprocess

def detect_hardware():
    """
    Detects the available hardware for processing.
    Checks for CUDA first, then identifies the CPU vendor.

    Returns:
        tuple: A tuple containing ('device_type', 'device_name').
               e.g., ('cuda', 'NVIDIA GeForce RTX 4070'),
                     ('cpu', 'intel'),
                     ('cpu', 'amd')
    """
    # Check for NVIDIA GPU with CUDA
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            gpu_name = result.stdout.strip().split('\n')[0]
            return 'cuda', gpu_name
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass

    try:
        info = cpuinfo.get_cpu_info()
        brand = info.get('brand_raw', '')
        brand_lower = brand.lower()
        if 'intel' in brand_lower:
            return 'cpu', brand
        if 'amd' in brand_lower:
            return 'cpu', brand
    except Exception:
        # Fallback to platform module
        processor_brand = platform.processor()
        if 'intel' in processor_brand.lower():
             return 'cpu', processor_brand
        if 'amd' in processor_brand.lower():
             return 'cpu', processor_brand

    return 'cpu', 'Unknown CPU'