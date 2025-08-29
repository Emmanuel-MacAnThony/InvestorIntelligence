"""
Direct Airtable client for monolithic Streamlit app
"""

import os
import requests
import streamlit as st
from typing import Dict, List, Any, Optional


class AirtableClient:
    """Direct Airtable API client."""
    
    def __init__(self):
        # Get API key from environment
        self.api_key = None
        for key in ["AIRTABLE_API_KEY", "AIRTABLE_ACCESS_TOKEN", "AIRTABLE_PAT"]:
            value = os.getenv(key)
            if value:
                self.api_key = value
                break
        
        if not self.api_key:
            st.error("❌ No Airtable API key found. Set AIRTABLE_API_KEY in your environment.")
        
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        self.base_url = "https://api.airtable.com/v0"
    
    def get_bases(self) -> List[Dict[str, Any]]:
        """Get all accessible Airtable bases."""
        if not self.api_key:
            return []
        
        try:
            url = f"{self.base_url}/meta/bases"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json().get("bases", [])
            else:
                st.error(f"Failed to fetch bases: {response.status_code}")
                return []
        except Exception as e:
            st.error(f"Error fetching bases: {e}")
            return []
    
    def get_tables(self, base_id: str) -> List[Dict[str, Any]]:
        """Get tables in a base."""
        if not self.api_key:
            return []
        
        try:
            url = f"{self.base_url}/meta/bases/{base_id}/tables"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json().get("tables", [])
            else:
                st.error(f"Failed to fetch tables: {response.status_code}")
                return []
        except Exception as e:
            st.error(f"Error fetching tables: {e}")
            return []
    
    def get_records(self, base_id: str, table_id: str, view_name: str = None, 
                   page_size: int = 100, offset: str = None, 
                   fields: List[str] = None) -> Dict[str, Any]:
        """Get records from a table/view."""
        if not self.api_key:
            return {"records": [], "offset": None}
        
        try:
            url = f"{self.base_url}/{base_id}/{table_id}"
            params = {"pageSize": min(page_size, 100)}
            
            if view_name and view_name != "Grid view":
                params["view"] = view_name
            if offset:
                params["offset"] = offset
            if fields:
                for field in fields:
                    params.setdefault("fields[]", []).append(field)
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "records": data.get("records", []),
                    "offset": data.get("offset")
                }
            else:
                st.error(f"Failed to fetch records: {response.status_code}")
                return {"records": [], "offset": None}
                
        except Exception as e:
            st.error(f"Error fetching records: {e}")
            return {"records": [], "offset": None}
    
    def create_record(self, base_id: str, table_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Create a record in a table."""
        if not self.api_key:
            return {"error": "No API key"}
        
        try:
            url = f"{self.base_url}/{base_id}/{table_id}"
            payload = {"fields": fields}
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                error_msg = f"Failed to create record: {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error_msg += f" - {error_data['error'].get('message', '')}"
                    except:
                        pass
                st.error(error_msg)
                return {"error": error_msg}
        except Exception as e:
            st.error(f"Error creating record: {e}")
            return {"error": str(e)}
    
    def update_record(self, base_id: str, table_id: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record in a table."""
        if not self.api_key:
            return {"error": "No API key"}
        
        try:
            url = f"{self.base_url}/{base_id}/{table_id}/{record_id}"
            payload = {"fields": fields}
            
            response = requests.patch(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Failed to update record: {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error_msg += f" - {error_data['error'].get('message', '')}"
                    except:
                        pass
                st.error(error_msg)
                return {"error": error_msg}
        except Exception as e:
            st.error(f"Error updating record: {e}")
            return {"error": str(e)}


# Global instance
_airtable_client = None

def get_airtable_client() -> AirtableClient:
    """Get global Airtable client instance."""
    global _airtable_client
    if _airtable_client is None:
        _airtable_client = AirtableClient()
    return _airtable_client