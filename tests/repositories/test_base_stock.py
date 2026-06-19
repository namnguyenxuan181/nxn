import pytest
from repositories.base_stock import BaseStockRepository
from models.stock_price import StockPrice


def test_base_stock_repository_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseStockRepository()


def test_concrete_stock_repository_must_implement_save():
    class IncompleteStockRepository(BaseStockRepository):
        pass

    with pytest.raises(TypeError):
        IncompleteStockRepository()


def test_concrete_stock_repository_works_when_save_implemented():
    class OkStockRepository(BaseStockRepository):
        def save(self, records: list[StockPrice]) -> None:
            pass

    OkStockRepository().save([])
