import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from core.config import DATA_DIR

NOTEBOOKS_FILE = DATA_DIR / "notebooks.json"

class NotebookManager:
    def __init__(self, storage_file: Path = NOTEBOOKS_FILE):
        self.storage_file = storage_file
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

    def _normalize_notebook(self, nb: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures notebook has doc_names list format."""
        if "doc_names" not in nb:
            if nb.get("doc_name"):
                nb["doc_names"] = [nb["doc_name"]]
            else:
                nb["doc_names"] = []
        # Keep doc_names as clean list
        nb["doc_names"] = list(dict.fromkeys([d for d in nb["doc_names"] if d]))
        return nb

    def load_all(self) -> Dict[str, Any]:
        """Loads all notebooks and active notebook ID, normalizing document lists."""
        if not self.storage_file.exists():
            initial_id = str(uuid.uuid4())[:8]
            data = {
                "active_id": initial_id,
                "notebooks": {
                    initial_id: {
                        "id": initial_id,
                        "title": "Cuaderno Principal",
                        "doc_names": [],
                        "created_at": datetime.now().isoformat(),
                        "messages": []
                    }
                }
            }
            self.save_all(data)
            return data

        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not data.get("notebooks"):
                    initial_id = str(uuid.uuid4())[:8]
                    data = {
                        "active_id": initial_id,
                        "notebooks": {
                            initial_id: {
                                "id": initial_id,
                                "title": "Cuaderno Principal",
                                "doc_names": [],
                                "created_at": datetime.now().isoformat(),
                                "messages": []
                            }
                        }
                    }
                    self.save_all(data)
                    return data

                # Normalize each notebook
                for nb_id in data["notebooks"]:
                    data["notebooks"][nb_id] = self._normalize_notebook(data["notebooks"][nb_id])

                if data.get("active_id") not in data["notebooks"]:
                    data["active_id"] = list(data["notebooks"].keys())[0]

                return data
        except Exception:
            initial_id = str(uuid.uuid4())[:8]
            return {
                "active_id": initial_id,
                "notebooks": {
                    initial_id: {
                        "id": initial_id,
                        "title": "Cuaderno Principal",
                        "doc_names": [],
                        "created_at": datetime.now().isoformat(),
                        "messages": []
                    }
                }
            }

    def save_all(self, data: Dict[str, Any]):
        """Persists all notebooks to disk."""
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error guardando cuadernos: {e}")

    def create_notebook(self, title: str = "Nuevo Cuaderno", doc_names: Optional[List[str]] = None) -> Dict[str, Any]:
        data = self.load_all()
        new_id = str(uuid.uuid4())[:8]
        new_nb = {
            "id": new_id,
            "title": title,
            "doc_names": doc_names or [],
            "created_at": datetime.now().isoformat(),
            "messages": []
        }
        data["notebooks"][new_id] = new_nb
        data["active_id"] = new_id
        self.save_all(data)
        return new_nb

    def delete_notebook(self, notebook_id: str):
        data = self.load_all()
        if notebook_id in data["notebooks"]:
            del data["notebooks"][notebook_id]
            if not data["notebooks"]:
                new_id = str(uuid.uuid4())[:8]
                data["notebooks"][new_id] = {
                    "id": new_id,
                    "title": "Cuaderno Principal",
                    "doc_names": [],
                    "created_at": datetime.now().isoformat(),
                    "messages": []
                }
                data["active_id"] = new_id
            elif data["active_id"] == notebook_id:
                data["active_id"] = list(data["notebooks"].keys())[0]
            self.save_all(data)

    def set_active(self, notebook_id: str):
        data = self.load_all()
        if notebook_id in data["notebooks"]:
            data["active_id"] = notebook_id
            self.save_all(data)

    def update_notebook(self, notebook_id: str, updates: Dict[str, Any]):
        data = self.load_all()
        if notebook_id in data["notebooks"]:
            data["notebooks"][notebook_id].update(updates)
            data["notebooks"][notebook_id] = self._normalize_notebook(data["notebooks"][notebook_id])
            self.save_all(data)

    def add_document_to_notebook(self, notebook_id: str, doc_name: str):
        data = self.load_all()
        if notebook_id in data["notebooks"]:
            nb = data["notebooks"][notebook_id]
            docs = nb.get("doc_names", [])
            if doc_name not in docs:
                docs.append(doc_name)
                nb["doc_names"] = docs
                self.save_all(data)

    def remove_document_from_notebook(self, notebook_id: str, doc_name: str):
        data = self.load_all()
        if notebook_id in data["notebooks"]:
            nb = data["notebooks"][notebook_id]
            docs = [d for d in nb.get("doc_names", []) if d != doc_name]
            nb["doc_names"] = docs
            self.save_all(data)

    def remove_document_from_all_notebooks(self, doc_name: str):
        """Removes a document from all notebooks when it is permanently deleted."""
        data = self.load_all()
        changed = False
        for nb_id, nb in data.get("notebooks", {}).items():
            docs = nb.get("doc_names", [])
            if doc_name in docs:
                nb["doc_names"] = [d for d in docs if d != doc_name]
                changed = True
        if changed:
            self.save_all(data)
