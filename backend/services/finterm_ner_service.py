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
        'keywords': ['股票', '股权', '股本', '普通股', '优先股', '股份', 'A股', '港股', '美股', 'A-share', 'B-share', 'H-share', 'N-share', 'S-share', 'A-Share', 'B-Share', 'H-Share', 'N-Share', 'S-Share']
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
        'keywords': ['贷款', '融资', '信贷', '票据', '商业票据', '融资券', '信用证', '银团贷款', 'A Round Financing', 'B Round Financing', 'C Round Financing', 'Seed Round', 'Series A', 'Series B', 'Series C', 'Venture Capital', 'Private Equity', 'IPO', 'Initial Public Offering', 'ABA Bank Index']
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
        # 获取偏移量映射以保留原始文本格式
        inputs = self.tokenizer(text, return_tensors="pt",
                              truncation=True,
                              max_length=512,
                              return_offsets_mapping=True)

        offset_mapping = inputs.pop('offset_mapping').squeeze(0)

        with torch.no_grad():
            outputs = self.model(**inputs)

        # 获取预测结果和置信度
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        preds = torch.argmax(probs, dim=-1)[0]
        confs = torch.max(probs, dim=-1).values[0]

        # 获取tokens用于处理
        token_ids = inputs["input_ids"][0].tolist()
        tokens = self.tokenizer.convert_ids_to_tokens(token_ids)

        # 使用偏移量映射重建术语
        results = []
        current_term = []
        current_conf = []
        current_indices = []

        for i, (token, pred, conf, offset) in enumerate(zip(tokens, preds, confs, offset_mapping)):
            start, end = offset.tolist()

            # 跳过特殊token
            if token in ["[CLS]", "[SEP]", "[PAD]"] or start == end:
                continue

            label = self.label_map.get(pred.item(), "O")
            conf = conf.item()

            # 只处理金融术语标签且置信度达标
            if label == "B-FIN" and conf >= min_confidence:
                # 保存当前术语
                if current_term and len("".join(current_term)) >= self.min_term_length:
                    term_text = self._reconstruct_term(text, current_indices)
                    avg_conf = sum(current_conf) / len(current_conf)
                    start_pos = current_indices[0][0] if current_indices else 0
                    end_pos = current_indices[-1][1] if current_indices else 0
                    
                    results.append({
                        "term": term_text,
                        "confidence": avg_conf,
                        "start_pos": start_pos,
                        "end_pos": end_pos,
                        "label": "FIN"
                    })

                # 开始新术语
                current_term = [text[start:end]]
                current_conf = [conf]
                current_indices = [(start, end)]

            elif label == "I-FIN" and current_term and conf >= min_confidence:
                # 继续当前术语
                current_term.append(text[start:end])
                current_conf.append(conf)
                current_indices.append((start, end))

            else:
                # 非金融术语，结束当前术语
                if current_term and len("".join(current_term)) >= self.min_term_length:
                    term_text = self._reconstruct_term(text, current_indices)
                    avg_conf = sum(current_conf) / len(current_conf)
                    start_pos = current_indices[0][0] if current_indices else 0
                    end_pos = current_indices[-1][1] if current_indices else 0
                    
                    results.append({
                        "term": term_text,
                        "confidence": avg_conf,
                        "start_pos": start_pos,
                        "end_pos": end_pos,
                        "label": "FIN"
                    })
                current_term = []
                current_conf = []
                current_indices = []

        # 添加最后一个术语
        if current_term and len("".join(current_term)) >= self.min_term_length:
            term_text = self._reconstruct_term(text, current_indices)
            avg_conf = sum(current_conf) / len(current_conf)
            start_pos = current_indices[0][0] if current_indices else 0
            end_pos = current_indices[-1][1] if current_indices else 0
            
            results.append({
                "term": term_text,
                "confidence": avg_conf,
                "start_pos": start_pos,
                "end_pos": end_pos,
                "label": "FIN"
            })

        return results

    def _reconstruct_term(self, text, indices):
        """使用原始文本偏移量重建术语"""
        if not indices:
            return ""

        # 按起始位置排序
        indices.sort(key=lambda x: x[0])

        # 重建术语文本
        term_text = ""
        prev_end = indices[0][0]

        for start, end in indices:
            # 添加缺失的文本（如空格）
            if start > prev_end:
                term_text += text[prev_end:start]
            term_text += text[start:end]
            prev_end = end

        return term_text
    


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

def generate_highlighted_text(text, entities):
    """生成带有高亮标记的文本"""
    if not entities:
        return text
    
    # 按开始位置排序实体
    sorted_entities = sorted(entities, key=lambda x: x["开始字符位置"])
    
    # 构建高亮文本
    highlighted_parts = []
    last_end = 0
    
    for entity in sorted_entities:
        start_pos = entity["开始字符位置"]
        end_pos = entity["结束字符位置"]
        entity_text = entity["识别实体"]
        entity_type = entity.get("实体分类", "FIN")
        
        # 添加实体前的普通文本
        if start_pos > last_end:
            highlighted_parts.append({
                "text": text[last_end:start_pos],
                "type": "normal",
                "highlight": False
            })
        
        # 添加高亮的实体文本
        highlighted_parts.append({
            "text": entity_text,
            "type": "entity",
            "entity_type": entity_type,
            "highlight": True,
            "start_pos": start_pos,
            "end_pos": end_pos,
            "confidence": entity.get("识别分数", 0)
        })
        
        last_end = end_pos
    
    # 添加最后的普通文本
    if last_end < len(text):
        highlighted_parts.append({
            "text": text[last_end:],
            "type": "normal",
            "highlight": False
        })
    
    return highlighted_parts

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
        # 对于英文术语，使用不区分大小写的匹配
        if any(c.isascii() for c in term):
            # 英文术语，使用不区分大小写的正则表达式
            pattern = re.compile(re.escape(term), re.IGNORECASE)
        else:
            # 中文术语，使用区分大小写的匹配
            pattern = re.compile(re.escape(term))
            
        for match in pattern.finditer(text):
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
            print(f"\n=== NER模型识别结果 ===")
            # 使用新的识别器，降低置信度阈值以捕获更多实体
            predicted_terms = recognizer.predict(text, min_confidence=0.4)
            
            print(f"模型识别到 {len(predicted_terms)} 个候选实体:")
            
            for i, term_info in enumerate(predicted_terms, 1):
                term = term_info["term"]
                confidence = term_info["confidence"]
                start_pos = term_info["start_pos"]
                end_pos = term_info["end_pos"]
                
                print(f"  {i}. 实体: '{term}'")
                print(f"     置信度: {confidence:.4f}")
                print(f"     位置: [{start_pos}, {end_pos}]")
                print(f"     长度: {len(term)} 字符")
                
                # 过滤掉太长的实体（可能是整个句子）
                if len(term) > 50:  # 如果实体超过50个字符，跳过
                    print(f"     ✗ 跳过：实体太长")
                    continue
                    
                # 分配实体类型
                entity_type = assign_entity_type(term, selected_classifications)
                print(f"     分类: {entity_type}")
                print(f"     ✓ 保留")
                
                entities.append({
                    "原始单词": term,
                    "识别实体": term,
                    "实体分类": entity_type,
                    "识别分数": round(float(confidence), 4),
                    "开始字符位置": start_pos,
                    "结束字符位置": end_pos
                })
            
            print(f"模型最终保留 {len(entities)} 个实体")
        
        # 使用规则引擎作为补充，确保能识别到所有预定义的金融术语
        print(f"\n=== 规则引擎识别结果 ===")
        rule_entities = extract_entities_with_rule_engine(text, selected_classifications)
        
        print(f"规则引擎识别到 {len(rule_entities)} 个实体:")
        for i, entity in enumerate(rule_entities, 1):
            term = entity.get("识别实体", "")
            category = entity.get("实体分类", "")
            score = entity.get("识别分数", "")
            start_pos = entity.get("开始字符位置", "")
            end_pos = entity.get("结束字符位置", "")
            
            print(f"  {i}. 实体: '{term}'")
            print(f"     分类: {category}")
            print(f"     置信度: {score}")
            print(f"     位置: [{start_pos}, {end_pos}]")
        
        entities.extend(rule_entities)
        print(f"合并后总实体数: {len(entities)}")
        
        # 去重和过滤逻辑
        print(f"\n=== 去重和过滤过程 ===")
        
        # 1. 首先按长度排序，优先保留更长的匹配项
        entities.sort(key=lambda x: len(x.get("识别实体", "")), reverse=True)
        print(f"按长度排序后的实体:")
        for i, entity in enumerate(entities, 1):
            term = entity.get("识别实体", "")
            print(f"  {i}. '{term}' (长度: {len(term)})")
        
        # 2. 过滤掉重叠的实体，优先保留更长的
        filtered_entities = []
        for entity in entities:
            term = entity.get("识别实体", "").strip()
            start_pos = entity.get("开始字符位置", 0)
            end_pos = entity.get("结束字符位置", 0)
            
            print(f"\n检查实体: '{term}' (位置: [{start_pos}, {end_pos}])")
            
            # 跳过空实体或太短的实体
            if not term or len(term) < 3:
                print(f"  ✗ 跳过：实体太短或为空")
                continue
                
            # 检查是否与已有实体重叠
            is_overlapping = False
            overlapping_entity = None
            for existing_entity in filtered_entities:
                existing_start = existing_entity.get("开始字符位置", 0)
                existing_end = existing_entity.get("结束字符位置", 0)
                existing_term = existing_entity.get("识别实体", "")
                
                # 检查重叠
                if (start_pos < existing_end and end_pos > existing_start):
                    is_overlapping = True
                    overlapping_entity = existing_term
                    break
            
            if is_overlapping:
                print(f"  ✗ 跳过：与已有实体 '{overlapping_entity}' 重叠")
            else:
                print(f"  ✓ 保留：无重叠")
                filtered_entities.append(entity)
        
        print(f"\n过滤后保留 {len(filtered_entities)} 个实体")
        
        # 3. 按开始位置排序
        sorted_entities = sorted(filtered_entities, key=lambda x: x["开始字符位置"])
        print(f"最终排序后的实体:")
        for i, entity in enumerate(sorted_entities, 1):
            term = entity.get("识别实体", "")
            start_pos = entity.get("开始字符位置", 0)
            end_pos = entity.get("结束字符位置", 0)
            score = entity.get("识别分数", 0)
            category = entity.get("实体分类", "")
            print(f"  {i}. '{term}' (位置: [{start_pos}, {end_pos}], 分数: {score}, 分类: {category})")
        
        # 构建返回结果
        result = {
            "status": "success",
            "用户输入内容": text,
            "选择分类": selected_classifications,
            "识别实体数": len(sorted_entities),
            "实体详情": sorted_entities,
            "高亮文本": generate_highlighted_text(text, sorted_entities),
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"命名实体识别处理失败: {str(e)}") 