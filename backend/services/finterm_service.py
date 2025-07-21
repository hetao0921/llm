from fastapi import APIRouter
from .finterm_loading_service import router as loading_router
from .finterm_ner_service import router as ner_router
from .finterm_normalization_service import router as normalization_router

# 创建主路由器
router = APIRouter()

# 将子服务路由器包含进来
router.include_router(loading_router, prefix="", tags=["金融术语加载"])
router.include_router(ner_router, prefix="", tags=["金融术语NER"])
router.include_router(normalization_router, prefix="", tags=["金融术语标准化"]) 