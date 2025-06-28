import sqlite3
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager

@dataclass
class Car:
    vin: str
    make: str
    model: str
    year: int

class DatabaseDriver:
    def __init__(self, db_path: str = "auto_db.sqlite"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create cars table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cars (
                    vin TEXT PRIMARY KEY,
                    make TEXT NOT NULL,
                    model TEXT NOT NULL,
                    year INTEGER NOT NULL
                )
            """)
            conn.commit()

    def create_car(self, vin: str, make: str, model: str, year: int) -> Car:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO cars (vin, make, model, year) VALUES (?, ?, ?, ?)",
                (vin, make, model, year)
            )
            conn.commit()
            return Car(vin=vin, make=make, model=model, year=year)

    def get_car_by_vin(self, vin: str) -> Optional[Car]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cars WHERE vin = ?", (vin,))
            row = cursor.fetchone()
            if not row:
                return None
            
            return Car(
                vin=row[0],
                make=row[1],
                model=row[2],
                year=row[3]
            )
