"""
Memory management and resource leak prevention for newsletter generation system.

This module provides comprehensive memory management, resource cleanup, and leak detection
to prevent memory accumulation during long-running operations.
"""

import gc
import logging
import os
import tempfile
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False
import threading
import time
import weakref
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from weakref import WeakSet

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    cpu_percent: float
    open_files: int
    connections: int
    timestamp: float
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceTracker:
    """Track resources for cleanup."""
    file_handles: Set[Any] = field(default_factory=set)
    temp_files: Set[Path] = field(default_factory=set)
    database_connections: WeakSet = field(default_factory=WeakSet)
    network_sessions: WeakSet = field(default_factory=WeakSet)
    cache_objects: WeakSet = field(default_factory=WeakSet)
    large_objects: WeakSet = field(default_factory=WeakSet)


class MemoryManager:
    """Comprehensive memory management for the newsletter system."""
    
    def __init__(self, enable_monitoring: bool = True):
        """Initialize memory manager.
        
        Args:
            enable_monitoring: Whether to enable continuous monitoring
        """
        self.enable_monitoring = enable_monitoring and HAS_PSUTIL
        self.process = psutil.Process() if HAS_PSUTIL else None
        self.initial_memory = self._get_memory_stats()
        self.peak_memory = self.initial_memory
        self.resource_tracker = ResourceTracker()
        self.monitoring_thread = None
        self.monitoring_active = False
        self.memory_history: List[MemoryStats] = []
        self.cleanup_callbacks: List[callable] = []
        
        # Memory limits (in MB)
        self.memory_warning_threshold = 1024  # 1GB
        self.memory_critical_threshold = 2048  # 2GB
        
        logger.info(f"Memory Manager initialized: {self.initial_memory.rss_mb:.1f}MB RSS")
    
    def _get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        if not HAS_PSUTIL or not self.process:
            # Return default stats when psutil is not available
            return MemoryStats(
                rss_mb=0.0,
                vms_mb=0.0,
                cpu_percent=0.0,
                open_files=0,
                connections=0,
                timestamp=time.time()
            )
            
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()
            
            # Get file descriptor count safely
            try:
                open_files = len(self.process.open_files())
            except (psutil.AccessDenied, OSError):
                open_files = -1
                
            # Get connection count safely
            try:
                connections = len(self.process.connections())
            except (psutil.AccessDenied, OSError):
                connections = -1
            
            return MemoryStats(
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                cpu_percent=cpu_percent,
                open_files=open_files,
                connections=connections,
                timestamp=time.time()
            )
        except Exception as e:
            logger.warning(f"Failed to get memory stats: {e}")
            return MemoryStats(0, 0, 0, 0, 0, time.time())
    
    def start_monitoring(self, interval: float = 30.0):
        """Start memory monitoring in background thread.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if not self.enable_monitoring or self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        def monitor():
            while self.monitoring_active:
                try:
                    stats = self._get_memory_stats()
                    self.memory_history.append(stats)
                    
                    # Keep only last 100 entries
                    if len(self.memory_history) > 100:
                        self.memory_history = self.memory_history[-100:]
                    
                    # Update peak memory
                    if stats.rss_mb > self.peak_memory.rss_mb:
                        self.peak_memory = stats
                    
                    # Check for memory warnings
                    self._check_memory_thresholds(stats)
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    logger.error(f"Memory monitoring error: {e}")
                    time.sleep(interval)
        
        self.monitoring_thread = threading.Thread(target=monitor, daemon=True)
        self.monitoring_thread.start()
        logger.info(f"Memory monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Stop memory monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        logger.info("Memory monitoring stopped")
    
    def _check_memory_thresholds(self, stats: MemoryStats):
        """Check if memory usage exceeds thresholds."""
        if stats.rss_mb > self.memory_critical_threshold:
            logger.critical(
                f"CRITICAL: Memory usage {stats.rss_mb:.1f}MB exceeds threshold {self.memory_critical_threshold}MB"
            )
            self.force_cleanup()
        elif stats.rss_mb > self.memory_warning_threshold:
            logger.warning(
                f"WARNING: Memory usage {stats.rss_mb:.1f}MB exceeds threshold {self.memory_warning_threshold}MB"
            )
    
    # === RESOURCE TRACKING ===
    
    def track_file_handle(self, file_handle: Any):
        """Track a file handle for cleanup."""
        self.resource_tracker.file_handles.add(file_handle)
    
    def track_temp_file(self, file_path: Union[str, Path]):
        """Track a temporary file for cleanup."""
        self.resource_tracker.temp_files.add(Path(file_path))
    
    def track_cache_object(self, cache_obj: Any):
        """Track a cache object for cleanup."""
        try:
            # Only track objects that can have weak references
            if hasattr(cache_obj, '__weakref__') or isinstance(cache_obj, (list, set)):
                self.resource_tracker.cache_objects.add(cache_obj)
            else:
                # For dict objects and other non-weakrefable objects, just log
                logger.debug(f"Skipping weak reference for {type(cache_obj).__name__} object")
        except (TypeError, AttributeError) as e:
            logger.debug(f"Cannot create weak reference for {type(cache_obj).__name__}: {e}")

    def track_large_object(self, obj: Any):
        """Track a large object for cleanup."""
        try:
            # Only track objects that can have weak references
            if hasattr(obj, '__weakref__') or isinstance(obj, (list, set)):
                self.resource_tracker.large_objects.add(obj)
            else:
                # For dict objects and other non-weakrefable objects, just log
                logger.debug(f"Skipping weak reference for {type(obj).__name__} object")
        except (TypeError, AttributeError) as e:
            logger.debug(f"Cannot create weak reference for {type(obj).__name__}: {e}")
    
    def track_connection(self, connection: Any):
        """Track a database/network connection."""
        if hasattr(connection, 'close'):
            self.resource_tracker.database_connections.add(connection)
        else:
            self.resource_tracker.network_sessions.add(connection)
    
    # === CLEANUP OPERATIONS ===
    
    def cleanup_temp_files(self):
        """Clean up tracked temporary files."""
        cleaned_count = 0
        for temp_path in list(self.resource_tracker.temp_files):
            try:
                if temp_path.exists():
                    temp_path.unlink()
                    cleaned_count += 1
                self.resource_tracker.temp_files.discard(temp_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} temporary files")
    
    def cleanup_file_handles(self):
        """Clean up tracked file handles."""
        cleaned_count = 0
        for handle in list(self.resource_tracker.file_handles):
            try:
                if hasattr(handle, 'close') and not handle.closed:
                    handle.close()
                    cleaned_count += 1
                self.resource_tracker.file_handles.discard(handle)
            except Exception as e:
                logger.warning(f"Failed to close file handle: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Closed {cleaned_count} file handles")
    
    def cleanup_connections(self):
        """Clean up database and network connections."""
        db_cleaned = 0
        net_cleaned = 0
        
        # Database connections
        for conn in list(self.resource_tracker.database_connections):
            try:
                if hasattr(conn, 'close'):
                    conn.close()
                    db_cleaned += 1
            except Exception as e:
                logger.warning(f"Failed to close database connection: {e}")
        
        # Network sessions
        for session in list(self.resource_tracker.network_sessions):
            try:
                if hasattr(session, 'close'):
                    session.close()
                    net_cleaned += 1
            except Exception as e:
                logger.warning(f"Failed to close network session: {e}")
        
        if db_cleaned > 0 or net_cleaned > 0:
            logger.info(f"Closed {db_cleaned} DB connections, {net_cleaned} network sessions")
    
    def cleanup_caches(self):
        """Clean up tracked cache objects."""
        cleaned_count = 0
        for cache_obj in list(self.resource_tracker.cache_objects):
            try:
                if hasattr(cache_obj, 'clear'):
                    cache_obj.clear()
                    cleaned_count += 1
                elif hasattr(cache_obj, '_cache') and hasattr(cache_obj._cache, 'clear'):
                    cache_obj._cache.clear()
                    cleaned_count += 1
                elif isinstance(cache_obj, dict):
                    cache_obj.clear()
                    cleaned_count += 1
                elif isinstance(cache_obj, list):
                    cache_obj.clear()
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"Failed to clear cache object: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleared {cleaned_count} cache objects")
    
    def force_garbage_collection(self):
        """Force garbage collection."""
        before_count = len(gc.get_objects())
        collected = gc.collect()
        after_count = len(gc.get_objects())
        
        logger.info(
            f"Garbage collection: {collected} objects collected, "
            f"{before_count} → {after_count} objects (-{before_count - after_count})"
        )
    
    def cleanup_all_resources(self):
        """Clean up all tracked resources."""
        logger.info("Starting comprehensive resource cleanup")
        
        self.cleanup_temp_files()
        self.cleanup_file_handles() 
        self.cleanup_connections()
        self.cleanup_caches()
        
        # Run custom cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f"Custom cleanup callback failed: {e}")
        
        self.force_garbage_collection()
        logger.info("Resource cleanup completed")
    
    def force_cleanup(self):
        """Force immediate cleanup of all resources."""
        logger.warning("Forcing immediate resource cleanup due to high memory usage")
        self.cleanup_all_resources()
    
    # === CONTEXT MANAGERS ===
    
    @contextmanager
    def track_memory_usage(self, operation_name: str = "operation"):
        """Context manager to track memory usage during an operation."""
        start_stats = self._get_memory_stats()
        start_time = time.time()
        
        try:
            yield
        finally:
            end_stats = self._get_memory_stats()
            duration = time.time() - start_time
            memory_delta = end_stats.rss_mb - start_stats.rss_mb
            
            log_level = logging.INFO
            if memory_delta > 100:  # More than 100MB increase
                log_level = logging.WARNING
            
            logger.log(
                log_level,
                f"Memory usage for {operation_name}: "
                f"{start_stats.rss_mb:.1f}MB → {end_stats.rss_mb:.1f}MB "
                f"(Δ{memory_delta:+.1f}MB) in {duration:.1f}s"
            )
    
    @contextmanager
    def temp_file_cleanup(self, prefix: str = "newsletter_", suffix: str = ".tmp"):
        """Context manager for automatic temporary file cleanup."""
        temp_path = None
        try:
            # Create temporary file
            fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
            os.close(fd)  # Close the file descriptor immediately
            temp_path = Path(temp_path)
            
            self.track_temp_file(temp_path)
            yield temp_path
            
        finally:
            # Cleanup
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                    self.resource_tracker.temp_files.discard(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")
    
    # === MONITORING AND REPORTING ===
    
    def add_cleanup_callback(self, callback: callable):
        """Add a custom cleanup callback."""
        self.cleanup_callbacks.append(callback)
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory usage report."""
        current_stats = self._get_memory_stats()
        
        return {
            "current_memory": {
                "rss_mb": current_stats.rss_mb,
                "vms_mb": current_stats.vms_mb,
                "cpu_percent": current_stats.cpu_percent,
                "open_files": current_stats.open_files,
                "connections": current_stats.connections
            },
            "peak_memory": {
                "rss_mb": self.peak_memory.rss_mb,
                "vms_mb": self.peak_memory.vms_mb,
                "timestamp": self.peak_memory.timestamp
            },
            "memory_growth": {
                "rss_delta_mb": current_stats.rss_mb - self.initial_memory.rss_mb,
                "vms_delta_mb": current_stats.vms_mb - self.initial_memory.vms_mb
            },
            "resource_counts": {
                "tracked_files": len(self.resource_tracker.file_handles),
                "temp_files": len(self.resource_tracker.temp_files),
                "cache_objects": len(self.resource_tracker.cache_objects),
                "large_objects": len(self.resource_tracker.large_objects)
            },
            "monitoring": {
                "enabled": self.enable_monitoring,
                "active": self.monitoring_active,
                "history_count": len(self.memory_history)
            }
        }
    
    def log_memory_report(self):
        """Log a detailed memory usage report."""
        report = self.get_memory_report()
        
        logger.info(
            "Memory Usage Report",
            extra={
                "current_rss_mb": report["current_memory"]["rss_mb"],
                "peak_rss_mb": report["peak_memory"]["rss_mb"],
                "growth_mb": report["memory_growth"]["rss_delta_mb"],
                "open_files": report["current_memory"]["open_files"],
                "tracked_resources": report["resource_counts"]
            }
        )
    
    def __enter__(self):
        """Context manager entry."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.stop_monitoring()
        self.cleanup_all_resources()
        self.log_memory_report()


# === GLOBAL MEMORY MANAGER ===

_global_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create the global memory manager."""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager()
    return _global_memory_manager


def cleanup_global_resources():
    """Clean up all global resources."""
    global _global_memory_manager
    if _global_memory_manager:
        _global_memory_manager.cleanup_all_resources()


# === DECORATOR FOR AUTOMATIC MEMORY MANAGEMENT ===

def track_memory_usage(operation_name: str = None):
    """Decorator to track memory usage of a function."""
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            with get_memory_manager().track_memory_usage(name):
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            with get_memory_manager().track_memory_usage(name):
                return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# === SPECIALIZED CLEANUP UTILITIES ===

def cleanup_image_processing_resources():
    """Specialized cleanup for image processing resources."""
    logger.info("Cleaning up image processing resources")
    
    # Clean up PIL image objects
    try:
        from PIL import Image
        # Force close any open images
        gc.collect()
    except ImportError:
        pass
    
    # Clean up OpenCV resources if available
    try:
        import cv2
        cv2.destroyAllWindows()
    except ImportError:
        pass


def cleanup_llm_client_resources():
    """Specialized cleanup for LLM client resources."""
    logger.info("Cleaning up LLM client resources")
    
    # This would be called by components to clean up their specific resources
    # Implementation depends on specific LLM clients used


def cleanup_database_connections():
    """Specialized cleanup for database connections."""
    logger.info("Cleaning up database connections")
    
    # Close any remaining Supabase connections
    # Implementation would depend on specific database clients


# === MEMORY LEAK DETECTION ===

class MemoryLeakDetector:
    """Simple memory leak detection based on growth patterns."""
    
    def __init__(self, growth_threshold_mb: float = 50.0, check_interval: int = 5):
        """Initialize leak detector.
        
        Args:
            growth_threshold_mb: Memory growth threshold in MB
            check_interval: Number of measurements to analyze
        """
        self.growth_threshold_mb = growth_threshold_mb
        self.check_interval = check_interval
        self.measurements = []
    
    def add_measurement(self, memory_mb: float):
        """Add a memory measurement."""
        self.measurements.append(memory_mb)
        
        # Keep only recent measurements
        if len(self.measurements) > self.check_interval * 2:
            self.measurements = self.measurements[-self.check_interval:]
    
    def detect_leak(self) -> Optional[Dict[str, Any]]:
        """Detect potential memory leak."""
        if len(self.measurements) < self.check_interval:
            return None
        
        recent_measurements = self.measurements[-self.check_interval:]
        
        # Calculate linear trend
        x = list(range(len(recent_measurements)))
        y = recent_measurements
        
        # Simple linear regression
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        # Slope = growth rate per measurement
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # If slope is positive and significant, potential leak
        if slope > self.growth_threshold_mb / self.check_interval:
            return {
                "leak_detected": True,
                "growth_rate_mb_per_measurement": slope,
                "estimated_growth_mb_per_hour": slope * 120,  # Assuming 30s intervals
                "confidence": min(1.0, slope / (self.growth_threshold_mb / self.check_interval))
            }
        
        return None