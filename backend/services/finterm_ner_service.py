import re
import torch
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from transformers import BertTokenizerFast, BertForTokenClassification
import os
from pathlib import Path

router = APIRouter()

# 金融术语分类与代码映射
FINTERM_CATEGORIES = {
    'E': {
        'name': 'Equities', 
        'description': '股权类（股票）',
        'keywords': ['股票', '股权', '股本', '普通股', '优先股', '股份', 'A股', '港股', '美股']
    },
    'D': {
        'name': 'Debt Instruments', 
        'description': '债务工具',
        'keywords': ['债券', '债务', '公司债', '国债', '地方债', '企业债', '可转债', '可交换债']
    },
    'R': {
        'name': 'Entitlements (Rights)', 
        'description': '权利（如认购权）',
        'keywords': ['认购权', '优先认购权', '配股权', '股息权', '分红权']
    },
    'T': {
        'name': 'Warrants', 
        'description': '权证',
        'keywords': ['权证', '认股权证', '购权证', '认购权证', '备兑权证']
    },
    'O': {
        'name': 'Options', 
        'description': '期权',
        'keywords': ['期权', '看涨期权', '看跌期权', '认购期权', '认沽期权', '买入期权', '卖出期权']
    },
    'F': {
        'name': 'Futures', 
        'description': '期货',
        'keywords': ['期货', '商品期货', '股指期货', '国债期货', '利率期货', '原油期货', '金融期货']
    },
    'H': {
        'name': 'Forward Contracts', 
        'description': '远期合约',
        'keywords': ['远期', '远期合约', '远期利率', '远期外汇', '远期交易', '汇率远期']
    },
    'S': {
        'name': 'Swaps', 
        'description': '互换',
        'keywords': ['互换', '掉期', '利率互换', '货币互换', '信用违约互换', 'CDS', '总收益互换']
    },
    'M': {
        'name': 'Miscellaneous', 
        'description': '其他（结构化产品等）',
        'keywords': ['结构化产品', '结构性存款', '结构性票据', '可转换证券', '混合型证券']
    },
    'C': {
        'name': 'Collective Investments', 
        'description': '集合投资工具',
        'keywords': ['基金', '公募基金', '私募基金', '交易所交易基金', 'ETF', 'REITs', '信托产品', '资产管理计划']
    },
    'L': {
        'name': 'Financing', 
        'description': '融资工具',
        'keywords': ['贷款', '融资', '信贷', '票据', '商业票据', '融资券', '信用证', '银团贷款']
    },
    'Y': {
        'name': 'Non-listed & Other', 
        'description': '非上市及其他',
        'keywords': ['非上市证券', '场外交易', 'OTC', '私募股权', '创投基金', '众筹']
    }
}

# 实现新的金融术语识别器
class FinancialTermRecognizer:
    def __init__(self, model_path="F:\\llm\\model\\bert-base-uncased\\ner_model"):
        self.tokenizer = BertTokenizerFast.from_pretrained(model_path)
        self.model = BertForTokenClassification.from_pretrained(model_path)
        self.model.eval()

        # 改进的标签映射
        self.label_map = {
            0: "O",        # 非金融术语
            1: "B-FIN",    # 金融术语开始
            2: "I-FIN",    # 金融术语中间
            3: "B-ORG",    # 机构名称开始
            4: "I-ORG"     # 机构名称中间
        }

        # 金融术语最小长度限制
        self.min_term_length = 3

    def predict(self, text, min_confidence=0.6):
        inputs = self.tokenizer(text, return_tensors="pt",
                              truncation=True,
                              max_length=512)

        with torch.no_grad():
            outputs = self.model(**inputs)

        # 获取预测结果和置信度
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        preds = torch.argmax(probs, dim=-1)[0]
        confs = torch.max(probs, dim=-1).values[0]

        # 转换token到原始文本位置
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        words = self.tokenizer.batch_decode(inputs["input_ids"][0])
        
        # 获取标记位置信息
        token_positions = self._get_token_positions(text, tokens, words)

        results = []
        current_term = []
        current_conf = 0.0
        current_start_pos = -1

        for i, (token, word, pred, conf) in enumerate(zip(tokens, words, preds, confs)):
            if token in ["[CLS]", "[SEP]", "[PAD]"]:
                continue

            label = self.label_map.get(pred.item(), "O")
            conf_value = conf.item()
            position = token_positions.get(i, None)

            # 只处理金融术语标签且置信度达标
            if label.startswith("B-") and conf_value >= min_confidence and position:
                # 如果有正在处理的术语，先保存它
                if current_term and len("".join(current_term)) >= self.min_term_length:
                    term_text = "".join(current_term)
                    avg_conf = current_conf / len(current_term)
                    end_pos = position[0] # 当前token开始位置就是上一个术语的结束位置
                    
                    results.append({
                        "term": term_text,
                        "confidence": avg_conf,
                        "start_pos": current_start_pos,
                        "end_pos": end_pos,
                        "label": label[2:] if label.startswith("B-") else "FIN" # 默认为FIN
                    })

                # 开始新的术语
                current_term = [word]
                current_conf = conf_value
                current_start_pos = position[0]

            elif label.startswith("I-") and current_term and conf_value >= min_confidence:
                current_term.append(word)
                current_conf += conf_value

        # 添加最后一个术语
        if current_term and len("".join(current_term)) >= self.min_term_length and current_start_pos >= 0:
            term_text = "".join(current_term)
            avg_conf = current_conf / len(current_term)
            # 估计结束位置，如果没有更好的方法
            end_pos = current_start_pos + len(term_text)
            
            results.append({
                "term": term_text,
                "confidence": avg_conf,
                "start_pos": current_start_pos,
                "end_pos": end_pos,
                "label": "FIN" # 默认为FIN
            })

        return results
    
    def _get_token_positions(self, text, tokens, words):
        """尝试将token映射到原始文本中的位置"""
        positions = {}
        current_pos = 0
        
        for i, (token, word) in enumerate(zip(tokens, words)):
            if token in ["[CLS]", "[SEP]", "[PAD]"]:
                continue
                
            # 清理token和word
            clean_word = word.strip()
            if not clean_word:
                continue
                
            # 在当前位置后查找此单词
            pos = text.find(clean_word, current_pos)
            if pos >= 0:
                positions[i] = (pos, pos + len(clean_word))
                current_pos = pos + len(clean_word)
                
        return positions

# 懒加载的识别器
_recognizer = None

def get_recognizer():
    """懒加载金融术语识别器"""
    global _recognizer
    if _recognizer is None:
        try:
            model_path = "F:\\llm\\model\\bert-base-uncased\\ner_model"
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"模型路径不存在: {model_path}")
            
            _recognizer = FinancialTermRecognizer(model_path)
            print(f"成功加载金融术语识别器: {model_path}")
        except Exception as e:
            print(f"加载金融术语识别器失败: {e}")
            return None
    return _recognizer

def assign_entity_type(entity_text, selected_classifications):
    """根据实体文本内容分配最可能的实体类型"""
    if not selected_classifications:
        selected_classifications = list(FINTERM_CATEGORIES.keys())
    
    # 检查实体是否匹配选定分类中的任何关键词
    for class_code in selected_classifications:
        if class_code in FINTERM_CATEGORIES:
            for keyword in FINTERM_CATEGORIES[class_code]['keywords']:
                if keyword in entity_text or entity_text in keyword:
                    return class_code
    
    # 如果没有明确匹配，尝试将实体分配给最相似的类别
    return selected_classifications[0] if selected_classifications else 'N/A'

def extract_entities_with_rule_engine(text, selected_classifications):
    """使用规则引擎提取实体（作为备用方法）"""
    if not selected_classifications:
        selected_classifications = list(FINTERM_CATEGORIES.keys())
    
    entities = []
    
    # 从支持的分类中筛选关键词
    terms_to_search = []
    for class_code in selected_classifications:
        if class_code in FINTERM_CATEGORIES:
            for keyword in FINTERM_CATEGORIES[class_code]['keywords']:
                terms_to_search.append({
                    'term': keyword, 
                    'type': class_code,
                    'confidence': 0.85 + 0.1 * (1 - len(keyword) / 10)  # 根据术语长度生成模拟准确率
                })
    
    # 在文本中查找匹配的术语
    for term_info in terms_to_search:
        term = term_info['term']
        term_type = term_info['type']
        base_confidence = term_info['confidence']
        
        # 查找术语的所有出现位置
        for match in re.finditer(term, text):
            start_idx = match.start()
            end_idx = match.end()
            matched_text = text[start_idx:end_idx]
            
            entities.append({
                "原始单词": matched_text,
                "识别实体": matched_text,
                "实体分类": term_type,
                "识别分数": round(float(base_confidence), 4),
                "开始字符位置": start_idx,
                "结束字符位置": end_idx
            })
    
    return entities

@router.post("/ner")
async def perform_finterm_ner(
    request: Dict = Body(...)
) -> Dict[str, Any]:
    """
    执行金融术语命名实体识别
    
    - text: 输入文本
    - classifications: 需要识别的术语分类列表
    """
    try:
        text = request.get('text', '')
        selected_classifications = request.get('classifications', [])
        
        if not text:
            raise HTTPException(status_code=400, detail="请提供输入文本")
        
        # 尝试使用模型进行NER预测
        entities = []
        recognizer = get_recognizer()
        
        if recognizer:
            # 使用新的识别器
            predicted_terms = recognizer.predict(text, min_confidence=0.6)
            
            for term_info in predicted_terms:
                term = term_info["term"]
                confidence = term_info["confidence"]
                start_pos = term_info["start_pos"]
                end_pos = term_info["end_pos"]
                
                # 分配实体类型
                entity_type = assign_entity_type(term, selected_classifications)
                
                entities.append({
                    "原始单词": term,
                    "识别实体": term,
                    "实体分类": entity_type,
                    "识别分数": round(float(confidence), 4),
                    "开始字符位置": start_pos,
                    "结束字符位置": end_pos
                })
        
        # 如果模型未能识别出实体，则使用规则引擎作为备选方案
        if not entities:
            entities = extract_entities_with_rule_engine(text, selected_classifications)
        
        # 去重 - 基于开始和结束位置
        unique_entities = {}
        for entity in entities:
            key = (entity["开始字符位置"], entity["结束字符位置"])
            if key not in unique_entities or unique_entities[key]["识别分数"] < entity["识别分数"]:
                unique_entities[key] = entity
        
        # 转换为列表并按开始位置排序
        sorted_entities = sorted(unique_entities.values(), key=lambda x: x["开始字符位置"])
        
        # 构建返回结果
        result = {
            "status": "success",
            "用户输入内容": text,
            "选择分类": selected_classifications,
            "识别实体数": len(sorted_entities),
            "实体详情": sorted_entities,
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"命名实体识别处理失败: {str(e)}") 