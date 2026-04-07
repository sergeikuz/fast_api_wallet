import asyncio
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient


async def test_health(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


async def test_list_wallets_empty(async_client: AsyncClient):
    response = await async_client.get("/api/v1/wallets")
    assert response.status_code == 200
    data = response.json()
    assert data["wallets"] == []
    assert data["total"] == 0


async def test_list_wallets(async_client: AsyncClient):
    wallet_id = uuid4()
    await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "100.00"},
    )
    response = await async_client.get("/api/v1/wallets")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    wallet_ids = [w["wallet_id"] for w in data["wallets"]]
    assert str(wallet_id) in wallet_ids


async def test_get_balance_not_found(async_client: AsyncClient):
    response = await async_client.get(f"/api/v1/wallets/{uuid4()}")
    assert response.status_code == 404


async def test_deposit_creates_wallet(async_client: AsyncClient):
    wallet_id = uuid4()
    response = await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "1000.00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["wallet_id"] == str(wallet_id)
    assert Decimal(data["balance"]) == Decimal("1000.00")
    assert "created_at" in data
    assert "updated_at" in data


async def test_get_balance(async_client: AsyncClient):
    wallet_id = uuid4()
    await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "500.50"},
    )
    response = await async_client.get(f"/api/v1/wallets/{wallet_id}")
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["balance"]) == Decimal("500.50")
    assert "created_at" in data
    assert "updated_at" in data


async def test_withdraw(async_client: AsyncClient):
    wallet_id = uuid4()
    await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "1000.00"},
    )
    response = await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "WITHDRAW", "amount": "300.00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["balance"]) == Decimal("700.00")


async def test_withdraw_insufficient_funds(async_client: AsyncClient):
    wallet_id = uuid4()
    await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "100.00"},
    )
    response = await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "WITHDRAW", "amount": "200.00"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient funds"


async def test_invalid_operation_type(async_client: AsyncClient):
    wallet_id = uuid4()
    response = await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "INVALID", "amount": "100.00"},
    )
    assert response.status_code == 422


async def test_invalid_amount_zero(async_client: AsyncClient):
    wallet_id = uuid4()
    response = await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "0"},
    )
    assert response.status_code == 422


async def test_invalid_amount_negative(async_client: AsyncClient):
    wallet_id = uuid4()
    response = await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "-50"},
    )
    assert response.status_code == 422


async def test_invalid_amount_three_decimals(async_client: AsyncClient):
    wallet_id = uuid4()
    response = await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "100.123"},
    )
    assert response.status_code == 422


async def test_malformed_json(async_client: AsyncClient):
    wallet_id = uuid4()
    response = await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


async def test_concurrent_deposits(async_client: AsyncClient):
    wallet_id = uuid4()
    num_requests = 10
    amount = "100.00"

    tasks = [
        async_client.post(
            f"/api/v1/wallets/{wallet_id}/operation",
            json={"operation_type": "DEPOSIT", "amount": amount},
        )
        for _ in range(num_requests)
    ]
    results = await asyncio.gather(*tasks)

    for r in results:
        assert r.status_code == 200

    response = await async_client.get(f"/api/v1/wallets/{wallet_id}")
    assert response.status_code == 200
    data = response.json()
    expected = Decimal(amount) * num_requests
    assert Decimal(data["balance"]) == expected


async def test_concurrent_mixed_operations(async_client: AsyncClient):
    wallet_id = uuid4()

    await async_client.post(
        f"/api/v1/wallets/{wallet_id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "1000.00"},
    )

    tasks = [
        async_client.post(
            f"/api/v1/wallets/{wallet_id}/operation",
            json={"operation_type": "WITHDRAW", "amount": "100.00"},
        )
        for _ in range(5)
    ]
    results = await asyncio.gather(*tasks)

    for r in results:
        assert r.status_code == 200

    response = await async_client.get(f"/api/v1/wallets/{wallet_id}")
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["balance"]) == Decimal("500.00")
