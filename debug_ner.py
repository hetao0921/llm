#!/usr/bin/env python3
"""
调试版本的NER测试脚本
"""

import torch
from transformers import BertTokenizerFast, BertForTokenClassification
import os

class DebugFinancialTermRecognizer:
    def __init__(self, model_path="F:\\llm\\model\\bert-base-uncased\\ner_model"):
        print(f"加载模型路径: {os.path.abspath(model_path)}")

        self.tokenizer = BertTokenizerFast.from_pretrained(model_path)
        self.model = BertForTokenClassification.from_pretrained(model_path)
        self.model.eval()

        # 标签映射说明：
        # 0: 非金融术语 (O)
        # 1: 金融术语开始 (B-FIN)
        # 2: 金融术语中间 (I-FIN)
        # 3: 机构名称开始 (B-ORG)
        # 4: 机构名称中间 (I-ORG)
        self.label_map = {
            0: "O",
            1: "B-FIN",
            2: "I-FIN",
            3: "B-ORG",
            4: "I-ORG"
        }

        self.min_term_length = 3

        print(f"模型权重加载自: {os.path.abspath(os.path.join(model_path, 'pytorch_model.bin'))}")
        print(f"模型配置加载自: {os.path.abspath(os.path.join(model_path, 'config.json'))}")
        print(f"Tokenizer加载自: {os.path.abspath(os.path.join(model_path, 'tokenizer.json'))}")

    def predict(self, text, min_confidence=0.6):
        print(f"\n预测输入文本: '{text}'")

        # 获取偏移量映射以保留原始文本格式
        inputs = self.tokenizer(text, return_tensors="pt",
                              truncation=True,
                              max_length=512,
                              return_offsets_mapping=True)

        offset_mapping = inputs.pop('offset_mapping').squeeze(0)

        # 打印token和偏移量详情
        print("\nToken处理详情:")
        token_ids = inputs["input_ids"][0].tolist()
        tokens = self.tokenizer.convert_ids_to_tokens(token_ids)

        for i, (token_id, token, offset) in enumerate(zip(token_ids, tokens, offset_mapping)):
            start, end = offset.tolist()
            print(f"Token {i}: ID={token_id}, Content='{token}'",
                  f"位置: [{start}, {end}]",
                  f"原始文本: '{text[start:end]}'" if start < end else "")

        with torch.no_grad():
            outputs = self.model(**inputs)

        # 获取预测结果和置信度
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        preds = torch.argmax(probs, dim=-1)[0]
        confs = torch.max(probs, dim=-1).values[0]

        # 打印每个token的预测结果
        print("\nToken预测详情:")
        for i, (token, pred, conf, offset) in enumerate(zip(tokens, preds, confs, offset_mapping)):
            start, end = offset.tolist()
            label = self.label_map.get(pred.item(), "O")
            token_text = text[start:end] if start < end else token
            print(f"Token {i}: '{token_text}' → {label} (置信度: {conf.item():.4f})")

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
                    
                    results.append((term_text, avg_conf, start_pos, end_pos))

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
                    
                    results.append((term_text, avg_conf, start_pos, end_pos))
                current_term = []
                current_conf = []
                current_indices = []

        # 添加最后一个术语
        if current_term and len("".join(current_term)) >= self.min_term_length:
            term_text = self._reconstruct_term(text, current_indices)
            avg_conf = sum(current_conf) / len(current_conf)
            start_pos = current_indices[0][0] if current_indices else 0
            end_pos = current_indices[-1][1] if current_indices else 0
            
            results.append((term_text, avg_conf, start_pos, end_pos))

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

if __name__ == "__main__":
    recognizer = DebugFinancialTermRecognizer()
    
    test_cases = [
        "A Round Financing",
        "A Round Financing.",
        "My company has A Round Financing",
        "A-share",
        "my company has a A-share."
    ]
    
    for test_text in test_cases:
        print("\n" + "="*60)
        terms = recognizer.predict(test_text)

        print("\n识别到的金融术语:")
        for term, conf, start, end in terms:
            print(f"- '{term}' (置信度: {conf:.2f}, 位置: [{start}, {end}])") 