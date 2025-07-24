import logging
import sys
from typing import Optional


class Logger:
    """Centralized logger for the application"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str, level: int = logging.INFO) -> logging.Logger:
        """Get or create a logger instance"""
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(level)
            
            if not logger.handlers:
                handler = logging.StreamHandler(sys.stdout)
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            
            cls._loggers[name] = logger
        
        return cls._loggers[name]