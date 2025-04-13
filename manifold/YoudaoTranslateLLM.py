"""
title: YouDao Translate LLM Pipeline
author: User
date: 2024-08-01
version: 1.0
license: MIT
description: A pipeline calling YouDao Cloud LLM translation API with streaming support
requirements: requests
"""

from typing import List, Union, Generator, Iterator
from pydantic import BaseModel
import requests
import json
import os
import hashlib
import uuid
import time


class Pipeline:
    class Valves(BaseModel):
        # API authentication info
        APP_KEY: str = ""
        APP_SECRET: str = ""
        TARGET_LANG: str = "zh"

    def __init__(self):
        self.type = "manifold"
        self.name = "YouDao Translate Pipeline"
        target_lang = os.environ.get("YOUDAO_TARGET_LANG", "zh")
        self.valves = self.Valves(**{"TARGET_LANG": target_lang})
        self.set_pipelines()

    def set_pipelines(self):
        models = ['youdao-translate']
        model_names = ['LLM Model']
        self.pipelines = [
            {"id": model, "name": name} for model, name in zip(models, model_names)
        ]
        print(f"youdao_translate_pipeline - models: {self.pipelines}")

    async def on_valves_updated(self):
        self.set_pipelines()
        pass

    async def on_startup(self):
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")
        pass

    def addAuthParams(self, app_key, app_secret, data):
        """Add YouDao API authentication parameters"""
        salt = str(uuid.uuid1())
        curtime = str(int(time.time()))
        sign_str = app_key + self.truncate(data["q"]) + salt + curtime + app_secret
        sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
        
        data["salt"] = salt
        data["sign"] = sign
        data["signType"] = "v3"
        data["curtime"] = curtime
        data["appKey"] = app_key
        
        return data

    def truncate(self, q):
        """Truncate q parameter"""
        if q is None:
            return None
        size = len(q)
        return q if size <= 20 else q[0:10] + str(size) + q[size - 10:size]

    def process_sse_stream(self, response):
        """Process SSE stream and generate incremental translation results formatted for OpenWebUI"""
        seen_data = set()  # Track processed data to avoid duplicates
        
        for line in response.iter_lines():
            if not line:
                continue
                
            line = line.decode('utf-8')
            
            # Skip event lines, we only care about data
            if line.startswith('event:'):
                continue
                
            if line.startswith('data:'):
                data = line[5:].strip()
                
                # Skip already processed data
                if data in seen_data:
                    continue
                    
                seen_data.add(data)
                
                try:
                    data_json = json.loads(data)
                    
                    # Process incremental translation
                    if "transIncre" in data_json:
                        # Generate OpenWebUI compatible SSE format data
                        output = json.dumps({"choices": [{"delta": {"content": data_json["transIncre"]}}]}, ensure_ascii=False)
                        yield f"data: {output}\n\n".encode('utf-8')
                    
                    # Handle error messages
                    elif "errorCode" in data_json and data_json["errorCode"] != "0":
                        error_msg = data_json.get("errorMsg", "Unknown error")
                        output = json.dumps({"choices": [{"delta": {"content": f"Error: {error_msg}"}}]}, ensure_ascii=False)
                        yield f"data: {output}\n\n".encode('utf-8')
                        # Only send error message once
                        break
                        
                except json.JSONDecodeError:
                    # If JSON parsing fails, API might have returned non-standard format
                    if "Unsupported" in data:
                        output = json.dumps({"choices": [{"delta": {"content": f"Error: {data}"}}]}, ensure_ascii=False)
                        yield f"data: {output}\n\n".encode('utf-8')
                        break
        
        # Send end marker
        yield f"data: [DONE]\n\n".encode('utf-8')

    def detect_polish_option(self, text: str) -> tuple[int, str]:
        """Automatically detect text domain and style to select appropriate polish option and prompt"""
        # Domain keyword mappings
        domain_keywords = {
            'literary': [
                'laughter', 'whisper', 'echo', 'sound', 'voice', 'music', 'dance', 'smile', 'tear',
                'heart', 'soul', 'spirit', 'mood', 'atmosphere', 'scene', 'moment', 'memory',
                'dream', 'night', 'dawn', 'sunset', 'rain', 'wind', 'storm', 'sea', 'mountain',
                'forest', 'garden', 'flower', 'tree', 'bird', 'shadow', 'light', 'dark', 'color',
                'taste', 'smell', 'touch', 'feel', 'emotion', 'feeling', 'mood', 'atmosphere',
                'whiskey', 'wine', 'bar', 'cafe', 'restaurant', 'hotel', 'room', 'house', 'street',
                'city', 'town', 'village', 'country', 'world', 'universe', 'time', 'space', 'life',
                'death', 'love', 'hate', 'joy', 'sorrow', 'hope', 'fear', 'courage', 'wisdom'
            ],
            'computer': [
                'program', 'code', 'software', 'hardware', 'computer', 'system', 'data', 'algorithm', 'network',
                'database', 'server', 'client', 'api', 'interface', 'function', 'class', 'object', 'variable',
                'loop', 'array', 'string', 'integer', 'float', 'boolean', 'debug', 'compile', 'runtime',
                'framework', 'library', 'package', 'module', 'dependency', 'version', 'git', 'repository',
                'cloud', 'container', 'docker', 'kubernetes', 'microservice', 'architecture', 'protocol',
                'encryption', 'security', 'authentication', 'authorization', 'token', 'session', 'cookie'
            ],
            'medical': [
                'patient', 'disease', 'treatment', 'symptom', 'diagnosis', 'medicine', 'hospital', 'doctor',
                'nurse', 'clinic', 'therapy', 'surgery', 'prescription', 'pharmacy', 'drug', 'vaccine',
                'virus', 'bacteria', 'infection', 'inflammation', 'chronic', 'acute', 'syndrome',
                'pathology', 'physiology', 'anatomy', 'neurology', 'cardiology', 'oncology', 'pediatrics',
                'psychiatry', 'dermatology', 'ophthalmology', 'orthopedics', 'gynecology', 'urology',
                'emergency', 'intensive care', 'rehabilitation', 'prognosis', 'mortality', 'morbidity'
            ],
            'biology': [
                'cell', 'gene', 'protein', 'organism', 'species', 'evolution', 'biology', 'genetic',
                'dna', 'rna', 'chromosome', 'mutation', 'enzyme', 'metabolism', 'photosynthesis',
                'respiration', 'ecosystem', 'biodiversity', 'taxonomy', 'phylogeny', 'morphology',
                'physiology', 'anatomy', 'microbiology', 'botany', 'zoology', 'ecology', 'marine biology',
                'molecular biology', 'cell biology', 'developmental biology', 'population genetics',
                'biochemistry', 'biotechnology', 'bioinformatics', 'genomics', 'proteomics', 'transcriptomics'
            ],
            'mechanical': [
                'machine', 'engine', 'mechanical', 'device', 'equipment', 'component', 'part',
                'gear', 'shaft', 'bearing', 'pump', 'motor', 'turbine', 'compressor', 'valve',
                'hydraulic', 'pneumatic', 'thermodynamics', 'fluid mechanics', 'heat transfer',
                'material science', 'metallurgy', 'welding', 'casting', 'forging', 'machining',
                'automation', 'robotics', 'control system', 'sensor', 'actuator', 'transmission',
                'clutch', 'brake', 'suspension', 'chassis', 'aerodynamics', 'propulsion',
                'manufacturing', 'production line', 'quality control', 'maintenance', 'repair'
            ],
            'finance': [
                'stock', 'bond', 'investment', 'portfolio', 'market', 'trading', 'broker', 'dividend',
                'interest', 'loan', 'mortgage', 'credit', 'debit', 'account', 'balance', 'transaction',
                'profit', 'loss', 'revenue', 'expense', 'asset', 'liability', 'equity', 'capital',
                'derivative', 'option', 'future', 'hedge', 'risk', 'return', 'yield', 'valuation',
                'analysis', 'forecast', 'budget', 'audit', 'tax', 'insurance', 'banking', 'fintech'
            ],
            'legal': [
                'law', 'legal', 'contract', 'agreement', 'clause', 'statute', 'regulation', 'compliance',
                'litigation', 'court', 'judge', 'jury', 'attorney', 'lawyer', 'plaintiff', 'defendant',
                'evidence', 'testimony', 'witness', 'hearing', 'trial', 'appeal', 'verdict', 'sentence',
                'jurisdiction', 'precedent', 'constitution', 'amendment', 'legislation', 'enforcement',
                'intellectual property', 'patent', 'copyright', 'trademark', 'license', 'permit'
            ]
        }
        
        # Style keyword mappings
        style_keywords = {
            'literary': [
                'metaphor', 'simile', 'imagery', 'symbol', 'allegory', 'personification',
                'hyperbole', 'irony', 'satire', 'allusion', 'alliteration', 'assonance',
                'rhythm', 'rhyme', 'meter', 'stanza', 'verse', 'prose', 'narrative',
                'descriptive', 'poetic', 'lyrical', 'elegant', 'graceful', 'beautiful',
                'vivid', 'colorful', 'rich', 'deep', 'profound', 'meaningful', 'symbolic',
                'artistic', 'creative', 'imaginative', 'expressive', 'evocative'
            ],
            'formal': [
                'therefore', 'thus', 'hence', 'consequently', 'furthermore', 'moreover', 'academic',
                'accordingly', 'subsequently', 'previously', 'aforementioned', 'aforedescribed',
                'herein', 'hereto', 'hereof', 'hereby', 'whereas', 'whereof', 'wherein', 'whereby',
                'pursuant to', 'in accordance with', 'subject to', 'notwithstanding', 'in lieu of',
                'in the event of', 'for the purpose of', 'in order to', 'with respect to', 'with regard to'
            ],
            'casual': [
                'hey', 'cool', 'awesome', 'great', 'nice', 'wow', 'yeah', 'okay', 'sure', 'whatever',
                'gonna', 'wanna', 'gotta', 'kinda', 'sorta', 'lots', 'tons', 'pretty', 'really',
                'totally', 'absolutely', 'definitely', 'probably', 'maybe', 'guess', 'think',
                'like', 'you know', 'right', 'haha', 'lol', 'omg', 'btw', 'imo', 'tbh', 'idk'
            ],
            'concise': [
                'brief', 'short', 'simple', 'direct', 'clear', 'concise', 'succinct', 'terse',
                'precise', 'exact', 'specific', 'focused', 'targeted', 'streamlined', 'efficient',
                'minimal', 'essential', 'core', 'key', 'main', 'primary', 'crucial', 'vital',
                'critical', 'important', 'significant', 'relevant', 'pertinent', 'applicable'
            ],
            'rich': [
                'elaborate', 'detailed', 'comprehensive', 'thorough', 'extensive', 'complete',
                'exhaustive', 'in-depth', 'profound', 'deep', 'broad', 'wide-ranging', 'all-encompassing',
                'all-inclusive', 'full', 'total', 'entire', 'whole', 'complete', 'comprehensive',
                'detailed', 'minute', 'precise', 'exact', 'accurate', 'specific', 'particular',
                'comprehensive', 'thorough', 'complete', 'exhaustive', 'extensive', 'detailed'
            ],
            'technical': [
                'parameter', 'variable', 'constant', 'function', 'method', 'algorithm', 'protocol',
                'interface', 'implementation', 'configuration', 'initialization', 'initialization',
                'deployment', 'integration', 'optimization', 'standardization', 'normalization',
                'validation', 'verification', 'authentication', 'authorization', 'encryption',
                'decryption', 'compression', 'decompression', 'serialization', 'deserialization'
            ]
        }
        
        text_lower = text.lower()
        
        # Default prompt for general translation
        default_prompt = """Please translate the following text with appropriate formatting and punctuation. 
Ensure the translation maintains the original meaning while being natural and fluent in the target language. 
Break long sentences into shorter ones where appropriate for better readability."""
        
        # Detect domain and set appropriate prompt
        for domain, keywords in domain_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                if domain == 'literary':
                    return 7, """Please translate the following literary text with careful attention to its artistic qualities.
Maintain the metaphorical expressions and vivid imagery while ensuring natural flow in the target language.
Pay special attention to:
1. Preserve metaphors and similes with culturally appropriate equivalents
2. Maintain the rhythm and flow of the text
3. Keep the emotional impact and atmosphere
4. Ensure proper formatting for dramatic effect
5. Preserve the sensory details and imagery
6. Keep the stylistic elements that create mood and tone
7. Maintain the balance between literal meaning and artistic expression"""
                elif domain == 'computer':
                    return 9, """Please translate the following technical text with appropriate computer science terminology. 
Maintain technical accuracy while ensuring the translation is clear and understandable. 
Use proper formatting for code-related terms and technical concepts."""
                elif domain == 'medical':
                    return 11, """Please translate the following medical text with appropriate medical terminology. 
Ensure accuracy in medical terms while maintaining clarity for the target audience. 
Use proper formatting for medical conditions, procedures, and medications."""
                elif domain == 'biology':
                    return 13, """Please translate the following biological text with appropriate scientific terminology. 
Maintain accuracy in biological terms while ensuring the translation is clear and precise. 
Use proper formatting for scientific names and biological processes."""
                elif domain == 'mechanical':
                    return 15, """Please translate the following mechanical engineering text with appropriate technical terminology. 
Ensure accuracy in mechanical terms while maintaining clarity for the target audience. 
Use proper formatting for technical specifications and mechanical processes."""
                elif domain == 'finance':
                    return 1, """Please translate the following financial text with appropriate financial terminology. 
Maintain accuracy in financial terms while ensuring the translation is clear and professional. 
Use proper formatting for financial figures and economic concepts."""
                elif domain == 'legal':
                    return 1, """Please translate the following legal text with appropriate legal terminology. 
Ensure accuracy in legal terms while maintaining the formal tone of legal documents. 
Use proper formatting for legal citations and references."""
        
        # Detect style and set appropriate prompt
        for style, keywords in style_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                if style == 'literary':
                    return 7, """Please translate the following text with careful attention to its literary qualities.
Focus on maintaining the artistic and stylistic elements while ensuring natural expression in the target language.
Consider:
1. The rhythm and flow of the language
2. The use of metaphors and imagery
3. The emotional resonance of the text
4. The cultural context and adaptations
5. The balance between accuracy and artistry
6. The preservation of stylistic devices
7. The overall aesthetic quality of the translation"""
                elif style == 'formal':
                    return 1, """Please translate the following formal text with appropriate professional language. 
Maintain the formal tone while ensuring the translation is clear and precise. 
Use proper formatting for formal documents and professional communication."""
                elif style == 'casual':
                    return 3, """Please translate the following casual text with appropriate conversational language. 
Maintain the casual tone while ensuring the translation is natural and engaging. 
Use proper formatting for informal communication and everyday language."""
                elif style == 'concise':
                    return 5, """Please translate the following text concisely while maintaining clarity. 
Focus on brevity and directness in the translation. 
Use proper formatting for clear and efficient communication."""
                elif style == 'rich':
                    return 7, """Please translate the following text with rich detail and descriptive language. 
Maintain the detailed nature of the content while ensuring the translation is engaging. 
Use proper formatting for descriptive passages and elaborate explanations."""
                elif style == 'technical':
                    return 9, """Please translate the following technical text with appropriate technical terminology. 
Maintain technical accuracy while ensuring the translation is clear and precise. 
Use proper formatting for technical specifications and processes."""
        
        # Default to rich polish with general prompt for potentially literary content
        return 7, """Please translate the following text with attention to both meaning and style.
Ensure the translation:
1. Maintains the original meaning and intent
2. Preserves any metaphorical or figurative language
3. Keeps the natural flow and rhythm
4. Uses appropriate formatting and punctuation
5. Adapts cultural references when necessary
6. Maintains the emotional tone and atmosphere
7. Ensures readability while preserving style"""

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        print(f"pipe:{__name__}")
        
        # Source is auto, target from environment or valve
        lang_from = 'auto'
        lang_to = self.valves.TARGET_LANG
        
        # Language code mapping
        lang_map = {
            'zh': 'zh-CHS',  # Chinese
            'en': 'en',      # English
            'ja': 'ja',      # Japanese
            'ko': 'ko',      # Korean
            'fr': 'fr'       # French
        }
        
        # Ensure correct language code
        to_code = lang_map.get(lang_to, lang_to)
        
        # Automatically detect polish option and get appropriate prompt
        polish_option, prompt = self.detect_polish_option(user_message)
        
        # Prepare request data
        data = {
            'q': user_message,
            'from': lang_from,
            'to': to_code,
            'i': user_message,
            'handleOption': '1',  # Use professional translation model
            'polishOption': str(polish_option),  # Use detected polish option
            'expandOption': '0',  # Disable expansion
            'prompt': prompt  # Add domain/style specific prompt
        }
        
        # Add authentication parameters
        data = self.addAuthParams(self.valves.APP_KEY, self.valves.APP_SECRET, data)
        
        # Prepare request headers
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/event-stream'
        }
        
        # Call API
        try:
            response = requests.post(
                'https://openapi.youdao.com/llm_trans',
                data=data,
                headers=headers,
                stream=True
            )
            
            if not response.ok:
                # Return error response
                def error_generator():
                    output = json.dumps({"choices": [{"delta": {"content": f"API Error: HTTP {response.status_code}"}}]}, ensure_ascii=False)
                    yield f"data: {output}\n\n".encode('utf-8')
                    yield f"data: [DONE]\n\n".encode('utf-8')
                return error_generator()
            
            # Use specialized processor to parse SSE events and return incremental translation content
            return self.process_sse_stream(response)
            
        except Exception as e:
            # Return exception error
            def error_generator():
                output = json.dumps({"choices": [{"delta": {"content": f"Translation error: {str(e)}"}}]}, ensure_ascii=False)
                yield f"data: {output}\n\n".encode('utf-8')
                yield f"data: [DONE]\n\n".encode('utf-8')
            return error_generator()


def main():
    """Local debugging function"""
    import asyncio
    
    async def test_translation():
        pipeline = Pipeline()
        pipeline.valves.APP_KEY = ""
        pipeline.valves.APP_SECRET = ""
        
        # Test texts for different domains and styles
        test_texts = [
            # Medical domain
            "The patient shows symptoms of fever and cough, requiring immediate medical attention.",
            # Computer domain
            "The program needs optimization for better performance and memory management.",
            # Biology domain
            "The DNA sequence replication process has been successfully completed in the laboratory.",
            # Mechanical domain
            "The mechanical components require regular maintenance and lubrication.",
            # Finance domain
            "The investment portfolio shows significant returns with minimal risk exposure.",
            # Legal domain
            "The contract terms and conditions are subject to applicable laws and regulations.",
            # Casual style
            "Hey, that's really cool! Let's hang out sometime and catch up.",
            # Concise style
            "Please provide a brief summary of the meeting outcomes.",
            # Rich style
            "The research paper presents a comprehensive analysis of the experimental data.",
            # Technical style
            "The API implementation requires proper authentication and authorization mechanisms."
        ]
        
        for text in test_texts:
            print(f"\nTranslating: {text}")
            result = pipeline.pipe(text, "youdao-translate", [], {})
            for chunk in result:
                print(chunk.decode('utf-8'), end='')
    
    # Run tests
    asyncio.run(test_translation())

if __name__ == "__main__":
    main() 