import json
import os
import re
import logging

from flask import Flask, jsonify, request, render_template
from psycopg_pool import ConnectionPool

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)


class ConnectionStringParser:
    """Utility class to parse connection strings into a dictionary."""

    @staticmethod
    def parse(conn_str: str) -> dict:
        """Convert a connection string into a dictionary."""
        conn_dict = {}
        parts = conn_str.split()
        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                conn_dict[key] = value
        return conn_dict


class CypherQueryFormatter:
    """Utility class for formatting Cypher queries for Apache AGE."""

    @staticmethod
    def format_query(graph_name: str, cypher_query: str) -> str:
        """
        Format the provided Cypher query for Apache AGE.

        Raises:
            ValueError: If the query is unsafe or incorrectly formatted.
        """
        if not CypherQueryFormatter.is_safe_cypher_query(cypher_query):
            raise ValueError("Unsafe query")

        # Append LIMIT 50 if no limit is specified.
        if "limit" not in cypher_query.lower():
            cypher_query += " LIMIT 50"

        returns = CypherQueryFormatter.extract_return_values(cypher_query)

        # Check for parameterized query usage.
        if re.findall(r"\$(\w+)", cypher_query):
            raise ValueError("Parameterized query")

        if returns:
            ag_types = ", ".join([f"{r} agtype" for r in returns])
            return f"SELECT * FROM cypher('{graph_name}', $$ {cypher_query} $$) AS ({ag_types});"
        else:
            raise ValueError("No return values specified")

    @staticmethod
    def is_safe_cypher_query(cypher_query: str) -> bool:
        """
        Ensure the Cypher query does not contain dangerous commands.

        Returns:
            bool: True if safe, False otherwise.
        """
        tokens = cypher_query.split()
        unsafe_keywords = ["create", "delete", "set", "remove", "merge"]
        return all(token.lower() not in unsafe_keywords for token in tokens)

    @staticmethod
    def extract_return_values(cypher_query: str) -> list:
        """
        Extract return values from the Cypher query.

        Returns:
            list: A list of strings representing identifiers.
        """
        match = re.search(r"(?i)(?<=\breturn\b)(.*)$", cypher_query)
        return_parts = []
        if match:
            return_parts = [x.strip() for x in match.group(1).strip().split(",")]
        return_values = []
        pattern = re.compile(r"([A-Za-z0-9_]\w*)\s*(?=\()")
        num_pattern = re.compile(r"^[0-9\.]+$")
        for return_part in return_parts:
            tokens = return_part.split()
            next_is_alias = False
            return_value = ""
            for token in tokens:
                token_lower = token.lower()
                if token_lower in ["as", "distinct"]:
                    next_is_alias = True
                    continue
                elif token_lower in [
                    "order",
                    "group",
                    "by",
                    "desc",
                    "asc",
                    "limit",
                    "skip",
                ]:
                    break
                elif token == "=":
                    break
                else:
                    return_value = token
                if next_is_alias:
                    return_value = token
                    break
            match_obj = pattern.match(return_value)
            if match_obj:
                return_value = match_obj.group(1)
            match_obj = num_pattern.match(return_value)
            if not match_obj:
                return_value = return_value.split(".")[0]
            if not re.search(r"[(){}]", return_value):
                return_values.append(return_value)
        return return_values


class DatabaseManager:
    """Class for managing database connections and queries."""

    def __init__(self):
        self.pool = None
        self.connection_info = {}  # 保存用

    def connect(self, connection_info: dict) -> None:
        """
        Connect to the database using provided connection information.

        Raises:
            Exception: If the connection fails.
        """
        host = connection_info.get("host", "localhost")
        port = connection_info.get("port", "5432")
        dbname = connection_info.get("dbname", "")
        user = connection_info.get("user", "")
        password = connection_info.get("password", "")

        # Construct the connection string with search_path options.
        conn_str = (
            f"host={host} port={port} dbname={dbname} user={user} password={password} "
            f"options='-c search_path=ag_catalog,\"$user\",public'"
        )

        # Initialize the connection pool and test the connection.
        self.pool = ConnectionPool(conninfo=conn_str)
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        self.connection_info = connection_info  # 保存接続情報
        logging.info("Database connection successful.")

    def execute_query(self, graph_name: str, cypher_query: str) -> dict:
        """
        Execute a formatted Cypher query and return nodes and edges.

        Raises:
            ValueError: For unsafe or invalid queries.
            Exception: For other unexpected errors.
        """
        if self.pool is None:
            raise ValueError("No database connection. Please connect first.")

        formatted_query = CypherQueryFormatter.format_query(graph_name, cypher_query)
        logging.info(f"Executing query: {formatted_query}")

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(formatted_query)
                try:
                    results = cur.fetchall()
                except Exception as fetch_error:
                    logging.error(f"Error fetching results: {fetch_error}")
                    results = []

        nodes = []
        edges = []
        # Process each result item to extract nodes and edges.
        for row in results:
            for item in row:
                if item.endswith("::vertex"):
                    try:
                        jsn = json.loads(item.rstrip("::vertex"))
                    except json.JSONDecodeError as e:
                        logging.error(f"JSON decode error for vertex: {e}")
                        continue
                    node = {
                        "id": jsn.get("id"),
                        "label": jsn.get("label"),
                        "properties": jsn.get("properties"),
                    }
                    nodes.append(node)
                elif item.endswith("::edge"):
                    try:
                        jsn = json.loads(item.rstrip("::edge"))
                    except json.JSONDecodeError as e:
                        logging.error(f"JSON decode error for edge: {e}")
                        continue
                    edge = {
                        "id": jsn.get("id"),
                        "label": jsn.get("label"),
                        "source": jsn.get("start_id"),
                        "target": jsn.get("end_id"),
                        "properties": jsn.get("properties"),
                    }
                    edges.append(edge)

        logging.info(f"Query result - Nodes: {nodes}, Edges: {edges}")
        return {"nodes": nodes, "edges": edges}

    def get_graph_info(self) -> list:
        """
        Retrieve information about graphs and their labels from the database.

        Returns:
            list: A list of graph information dictionaries.

        Raises:
            ValueError: If no database connection is established.
            Exception: For other unexpected errors.
        """
        if self.pool is None:
            raise ValueError("No database connection. Please connect first.")

        result = []
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                # Retrieve the list of graphs.
                cur.execute("SELECT graphid, name, namespace FROM ag_graph;")
                graphs = cur.fetchall()
                for graph in graphs:
                    graphid, graph_name, namespace = graph
                    # Retrieve label information for each graph.
                    cur.execute(
                        "SELECT name, kind, relation FROM ag_label WHERE graph = %s;",
                        (graphid,),
                    )
                    labels = cur.fetchall()
                    nodes = []
                    edges = []
                    for label in labels:
                        label_name, kind, relation = label
                        # Skip system labels (starting with '_').
                        if not label_name.startswith("_"):
                            try:
                                count_query = f"SELECT COUNT(*) FROM {relation};"
                                cur.execute(count_query)
                                count = cur.fetchone()[0]
                            except Exception as count_error:
                                logging.warning(
                                    f"Error counting records for relation {relation}: {count_error}"
                                )
                                count = None

                            if kind == "v":
                                nodes.append(
                                    {
                                        "name": label_name,
                                        "relation": relation,
                                        "count": count,
                                    }
                                )
                            elif kind == "e":
                                edges.append(
                                    {
                                        "name": label_name,
                                        "relation": relation,
                                        "count": count,
                                    }
                                )
                    result.append(
                        {
                            "graphid": graphid,
                            "graph_name": graph_name,
                            "namespace": namespace,
                            "nodes": nodes,
                            "edges": edges,
                        }
                    )
        return result


db_manager = DatabaseManager()


@app.route("/")
def index():
    """Render the main page with default connection info."""
    default_conn_str = os.environ.get("PG_CONNECTION_STRING", "")
    default_conn = (
        ConnectionStringParser.parse(default_conn_str) if default_conn_str else {}
    )
    return render_template("index.html", default_conn=default_conn)


@app.route("/api/connect", methods=["POST"])
def connect_db():
    """API endpoint to connect to the database."""
    data = request.get_json()
    connection_info = data.get("connection", {})
    try:
        db_manager.connect(connection_info)
        return jsonify({"message": "Successfully connected to the database!"})
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/connection_status", methods=["GET"])
def connection_status():
    """API endpoint to return the connection status."""
    status = "connected" if db_manager.pool is not None else "disconnected"
    return jsonify({"status": status, "connection_info": db_manager.connection_info})


@app.route("/api/execute_query", methods=["POST"])
def execute_query_endpoint():
    """API endpoint to execute a Cypher query."""
    data = request.get_json()
    cypher_query = data.get("cypher_query", "")
    graph_name = data.get("graph_name", "")

    if not cypher_query:
        return jsonify({"error": "No Cypher query specified"}), 400

    try:
        result = db_manager.execute_query(graph_name, cypher_query)
        return jsonify(result)
    except ValueError as ve:
        logging.error(f"Query error: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logging.error(f"Unexpected error during query execution: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/graph_info", methods=["GET"])
def graph_info():
    """API endpoint to retrieve graph information."""
    try:
        result = db_manager.get_graph_info()
        return jsonify(result)
    except ValueError as ve:
        logging.error(f"Graph info error: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logging.error(f"Unexpected error retrieving graph info: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
