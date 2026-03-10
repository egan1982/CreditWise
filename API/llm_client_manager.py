"""
LLM Client Manager Module
Manages lazy initialization of OpenAI client with support for LLM_Manager integration
Provides graceful degradation when API keys are not available
"""

import os
import json
import logging
from typing import Optional, Tuple
from pathlib import Path
from config import API_BASE

logger = logging.getLogger(__name__)

# Global client instance (lazy-loaded)
_llm_client = None
_llm_client_initialized = False
_llm_client_error = None


class LLMClientManager:
    """Manages LLM client initialization with graceful error handling"""
    
    @staticmethod
    def get_client(verbose: bool = True):
        """
        Get or initialize LLM client with graceful degradation
        
        Args:
            verbose: Whether to print initialization status
            
        Returns:
            OpenAI client instance or None if no API key available
        """
        global _llm_client, _llm_client_initialized, _llm_client_error
        
        if _llm_client_initialized:
            if _llm_client_error and verbose:
                print(f"[WARN] LLM Client Error: {_llm_client_error}")
            return _llm_client
        
        try:
            import openai
            
            # Try to get API key from multiple sources
            api_key = LLMClientManager._get_api_key()
            api_base = API_BASE
            
            if not api_key:
                _llm_client_error = "No API key found (OPENAI_API_KEY, DEEPSEEK_API_KEY, or LLM_Manager)"
                _llm_client = None
                _llm_client_initialized = True
                
                if verbose:
                    print(f"[INFO] {_llm_client_error}")
                    print("[INFO] LLM Chat API will not be available")
                    print("[INFO] Use LLM Manager UI to configure API keys: http://localhost:8200/llm-manager")
                return None
            
            # Initialize client
            _llm_client = openai.OpenAI(base_url=api_base, api_key=api_key)
            _llm_client_initialized = True
            
            if verbose:
                key_preview = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 12 else "****"
                logger.debug(f"LLM Client initialized: Base URL={api_base}, API Key={key_preview}")
            
            return _llm_client
            
        except Exception as e:
            _llm_client_error = str(e)
            _llm_client = None
            _llm_client_initialized = True
            
            if verbose:
                print(f"[ERROR] Failed to initialize LLM Client: {e}")
                print("[INFO] LLM Chat API will not be available")
            return None
    
    @staticmethod
    def _get_api_key() -> Optional[str]:
        """
        Try to get API key from multiple sources in order of preference
        
        Returns:
            API key string or None
        """
        # 1. Try environment variables
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            return api_key
        
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if api_key:
            return api_key
        
        # 2. Try LLM_Manager database
        try:
            db_path = Path("llm_manager.db")
            if db_path.exists():
                # Try to read LLM_Manager database
                api_key = LLMClientManager._get_key_from_llm_manager()
                if api_key:
                    return api_key
        except Exception:
            pass  # Silently ignore LLM_Manager database read errors
        
        return None
    
    @staticmethod
    def _get_key_from_llm_manager() -> Optional[str]:
        """
        Try to get API key from LLM_Manager database
        
        Returns:
            API key string or None
        """
        try:
            import sqlite3
            from pathlib import Path
            
            db_path = Path("llm_manager.db")
            if not db_path.exists():
                return None
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Try to query keys table
            cursor.execute("SELECT api_key FROM keys LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def is_available() -> bool:
        """Check if LLM client is available"""
        global _llm_client, _llm_client_initialized
        
        if not _llm_client_initialized:
            LLMClientManager.get_client(verbose=False)
        
        return _llm_client is not None
    
    @staticmethod
    def reset():
        """Reset client state (for testing)"""
        global _llm_client, _llm_client_initialized, _llm_client_error
        _llm_client = None
        _llm_client_initialized = False
        _llm_client_error = None
    
    @staticmethod
    def get_status() -> dict:
        """Get current LLM client status"""
        global _llm_client, _llm_client_initialized, _llm_client_error
        
        if not _llm_client_initialized:
            LLMClientManager.get_client(verbose=False)
        
        return {
            "available": _llm_client is not None,
            "initialized": _llm_client_initialized,
            "error": _llm_client_error
        }


def get_llm_client():
    """
    Module-level function to get LLM client
    Lazy initialization on first use
    """
    return LLMClientManager.get_client(verbose=False)
