"""
neo4j_connector.py — Connection manager for Neo4j AuraDB.

Usage:
    from database.neo4j_connector import get_driver, close_driver
"""

import os
from neo4j import GraphDatabase

_driver = None


def get_driver():
    """Get or create a Neo4j driver instance."""
    global _driver
    if _driver is None:
        uri = os.environ.get("NEO4J_URI")
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD")

        if not uri or not password:
            raise RuntimeError(
                "NEO4J_URI and NEO4J_PASSWORD must be set. "
                "Copy .env.example to .env and fill in your AuraDB credentials."
            )

        _driver = GraphDatabase.driver(uri, auth=(user, password))

        # Verify connectivity
        _driver.verify_connectivity()
        print(f"Connected to Neo4j at {uri}")

    return _driver


def close_driver():
    """Close the driver on shutdown."""
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def run_query(query, params=None):
    """Run a read query and return list of dicts."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, params or {})
        return [dict(record) for record in result]


def run_write(query, params=None):
    """Run a write query."""
    driver = get_driver()
    with driver.session() as session:
        session.run(query, params or {})
