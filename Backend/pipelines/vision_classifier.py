#!/usr/bin/env python3
"""
Vision LLM classifier for detailed object identification.
Integrates with the cropping pipeline to provide detailed descriptions.
"""

import base64
from pathlib import Path
from typing import List, Dict, Optional
import json


class VisionClassifier:
    def __init__(self, provider: str = "ollama", model: str = None):
        """
        Initialize vision classifier.
        
        Args:
            provider: 'openai', 'anthropic', 'google', or 'ollama'
            model: Model name (defaults to best available for provider)
        """
        self.provider = provider.lower()
        self.model = model
        self.client = None
        
        self._setup_client()
    
    def _setup_client(self):
        """Setup the appropriate API client."""
        if self.provider == "openai":
            import openai
            self.client = openai.OpenAI()
            self.model = self.model or "gpt-4o"
            
        elif self.provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic()
            self.model = self.model or "claude-3-5-sonnet-20241022"
            
        elif self.provider == "google":
            import google.generativeai as genai
            genai.configure()
            self.model = self.model or "gemini-1.5-flash"
            self.client = genai.GenerativeModel(self.model)
            
        elif self.provider == "ollama":
            import ollama
            self.client = ollama
            self.model = self.model or "qwen3-vl:8b"
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def classify_object(self, 
                       image_path: str, 
                       object_type: str = "object",
                       detail_level: str = "standard",
                       identify_person: bool = False) -> Dict:
        """
        Classify an object in detail using vision LLM.
        
        Args:
            image_path: Path to cropped image
            object_type: Generic type (e.g., 'bottle', 'person', 'car')
            detail_level: 'basic', 'standard', or 'detailed'
            identify_person: If True, attempt to identify the person by name
        
        Returns:
            Dictionary with classification results
        """
        # Adjust prompts based on object type
        if object_type == "person" and not identify_person:
            prompts = {
                "basic": "Describe the person's appearance briefly (clothing, pose, setting).",
                "standard": "Describe this person's appearance: clothing style, colors, pose, and setting. Do not attempt to identify who they are.",
                "detailed": """Describe the person's appearance in detail:
1. Clothing style and colors
2. Pose and body position
3. Setting/background
4. Accessories or items visible
5. Overall style/aesthetic
6. Lighting and image quality

Focus on visual description only, do not identify the individual."""
            }
        elif object_type == "person" and identify_person:
            prompts = {
                "basic": "Who is this person? If you recognize them, provide their name.",
                "standard": "Identify this person. If you recognize them, provide their name and a brief description of who they are (profession, known for, etc.).",
                "detailed": """Identify this person:
1. Name (if recognizable)
2. Profession or role
3. What they're known for
4. Physical appearance description
5. Clothing and style
6. Context clues in the image

If you cannot identify them, describe their appearance instead."""
            }
        else:
            prompts = {
                "basic": f"What type of {object_type} is this? Give a brief 1-2 word answer.",
                "standard": f"Identify this {object_type} specifically. What type/brand/style is it? Be concise but specific.",
                "detailed": f"""Analyze this {object_type} in detail:
                    1. Specific type/category
                    2. Brand (if visible)
                    3. Key visual characteristics
                    4. Color and material
                    5. Any text or labels visible
                    6. Estimated size/scale
                    7. Condition/quality
                Provide a structured response."""
            }
        
        prompt = prompts.get(detail_level, prompts["standard"])
        
        result = None
        if self.provider == "openai":
            result = self._classify_openai(image_path, prompt)
        elif self.provider == "anthropic":
            result = self._classify_anthropic(image_path, prompt)
        elif self.provider == "google":
            result = self._classify_google(image_path, prompt)
        elif self.provider == "ollama":
            result = self._classify_ollama(image_path, prompt)
        
        if result:
            result['mode'] = 'identify' if identify_person else 'describe'
        
        return result
    
    def _classify_openai(self, image_path: str, prompt: str) -> Dict:
        """Classify using OpenAI GPT-4 Vision."""
        base64_image = self._encode_image(image_path)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }],
            max_tokens=500
        )
        
        return {
            "description": response.choices[0].message.content,
            "model": self.model,
            "provider": "openai"
        }
    
    def _classify_anthropic(self, image_path: str, prompt: str) -> Dict:
        """Classify using Anthropic Claude."""
        base64_image = self._encode_image(image_path)
        
        # Detect image type
        ext = Path(image_path).suffix.lower()
        media_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp'
        }.get(ext, 'image/jpeg')
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )
        
        return {
            "description": response.content[0].text,
            "model": self.model,
            "provider": "anthropic"
        }
    
    def _classify_google(self, image_path: str, prompt: str) -> Dict:
        """Classify using Google Gemini."""
        from PIL import Image
        
        img = Image.open(image_path)
        response = self.client.generate_content([prompt, img])
        
        return {
            "description": response.text,
            "model": self.model,
            "provider": "google"
        }
    
    def _classify_ollama(self, image_path: str, prompt: str) -> Dict:
        """Classify using Ollama (local)."""
        # Convert image path to absolute path
        abs_path = str(Path(image_path).resolve())
        
        # Read and encode image as base64
        with open(abs_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        response = self.client.chat(
            model=self.model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_data]
            }]
        )
        
        return {
            "description": response['message']['content'],
            "model": self.model,
            "provider": "ollama"
        }
    
    def batch_classify(self, 
                      image_paths: List[str],
                      object_types: List[str] = None,
                      detail_level: str = "standard",
                      identify_person: bool = False) -> List[Dict]:
        """Classify multiple images."""
        if object_types is None:
            object_types = ["object"] * len(image_paths)
        
        results = []
        for img_path, obj_type in zip(image_paths, object_types):
            try:
                result = self.classify_object(img_path, obj_type, detail_level, identify_person)
                result['image_path'] = img_path
                results.append(result)
                mode = "Identified" if identify_person else "Classified"
                print(f"✓ {mode}: {Path(img_path).name}")
            except Exception as e:
                print(f"✗ Error classifying {img_path}: {e}")
                results.append({
                    'image_path': img_path,
                    'error': str(e)
                })
        
        return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Classify objects using vision LLMs"
    )
    parser.add_argument("images", nargs="+", help="Image files to classify")
    parser.add_argument("-p", "--provider", default="ollama",
                       choices=["openai", "anthropic", "google", "ollama"],
                       help="Vision model provider")
    parser.add_argument("-m", "--model", help="Specific model name")
    parser.add_argument("-t", "--type", default="object",
                       help="Object type hint (e.g., bottle, person, car)")
    parser.add_argument("-d", "--detail", default="standard",
                       choices=["basic", "standard", "detailed"],
                       help="Detail level")
    parser.add_argument("-o", "--output", help="Save results to JSON file")
    parser.add_argument("--identify", action="store_true",
                       help="Attempt to identify person by name (only for person type)")
    
    args = parser.parse_args()
    
    classifier = VisionClassifier(args.provider, args.model)
    
    results = classifier.batch_classify(
        args.images,
        [args.type] * len(args.images),
        args.detail,
        args.identify
    )
    
    # Print results
    print("\n" + "="*60)
    for result in results:
        if 'error' not in result:
            print(f"\n{Path(result['image_path']).name}:")
            print(f"{result['description']}")
            print(f"(Model: {result['model']})")
    
    # Save to JSON if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Results saved to {args.output}")


if __name__ == "__main__":
    main()
