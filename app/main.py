import logging
import time
import os
import psycopg

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel,Field
from dotenv import load_dotenv

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development")
DATABASE_URL = os.getenv("DATABASE_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="ResilioOps AI Order Service",
    version="1.0.0",
)

@app.get("/")
def home():
    logger.info("Home endpoint was called")

    return {
        "service": "ResilioOps AI Order Service",
        "message": "The application is running",
    }


@app.get("/health")
def health_check():
    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )
    
products = [
    {
        "id": 1,
        "name": "Laptop",
        "price": 999.99,
        "available": True,
    },
    {
        "id": 2,
        "name": "Headphones",
        "price": 149.99,
        "available": True,
    },
    {
        "id": 3,
        "name": "Keyboard",
        "price": 79.99,
        "available": False,
    },
]

class OrderRequest(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)

@app.get("/products")
def get_products():
    return {
        "count": len(products),
        "products": products,
    }

@app.get("/products/{product_id}")
def get_product(product_id: int):
    for product in products:
        if product["id"] == product_id:
            return product

    raise HTTPException(
        status_code=404,
        detail="Product not found",
    )

@app.post("/orders", status_code=201)
def create_order(order_request: OrderRequest):
    selected_product = None

    for product in products:
        if product["id"] == order_request.product_id:
            selected_product = product
            break

    if selected_product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    if not selected_product["available"]:
        raise HTTPException(
            status_code=409,
            detail="Product is currently unavailable",
        )

    total_price = selected_product["price"] * order_request.quantity

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO orders (
                    product_id,
                    product_name,
                    quantity,
                    total_price,
                    status
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING
                    id,
                    product_id,
                    product_name,
                    quantity,
                    total_price,
                    status,
                    created_at;
                """,
                (
                    order_request.product_id,
                    selected_product["name"],
                    order_request.quantity,
                    total_price,
                    "created",
                ),
            )

            row = cursor.fetchone()

    return {
        "id": row[0],
        "product_id": row[1],
        "product_name": row[2],
        "quantity": row[3],
        "total_price": float(row[4]),
        "status": row[5],
        "created_at": row[6],
    }

@app.get("/orders")
def get_orders():
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    product_id,
                    product_name,
                    quantity,
                    total_price,
                    status,
                    created_at
                FROM orders
                ORDER BY id;
                """
            )

            rows = cursor.fetchall()

    orders_from_db = []

    for row in rows:
        orders_from_db.append(
            {
                "id": row[0],
                "product_id": row[1],
                "product_name": row[2],
                "quantity": row[3],
                "total_price": float(row[4]),
                "status": row[5],
                "created_at": row[6],
            }
        )

    return {
        "count": len(orders_from_db),
        "orders": orders_from_db,
    }

@app.get("/simulate-error")
def simulate_error():
    raise HTTPException(
        status_code=500,
        detail="Simulated internal server error",
    )

@app.get("/simulate-slow")
def simulate_slow():
    time.sleep(5)

    return {
        "status": "success",
        "message": "This response was intentionally delayed by 5 seconds",
    }

@app.get("/info")
def get_info():
    return {
        "service": "ResilioOps AI Order Service",
        "environment": APP_ENV,
        "version": "1.0.0",
    }

@app.get("/db-check")
def database_check():
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()

    return {
        "database": "connected",
        "test_result": result[0],
    }
           
