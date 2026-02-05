# rag_service.py
import os
import chromadb
from django.conf import settings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAI
from dotenv import load_dotenv

import json
import re

load_dotenv()

class RAGService:
    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        
        # 1. ตั้งค่า Model (เหมือนเดิม)
        print("📥 Loading Embedding Model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': False}
        )

        if self.api_key:
            self.llm = GoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=self.api_key,
                temperature=0.7
            )
        else:
            self.llm = None

        # 2. เชื่อมต่อ ChromaDB (เปลี่ยนชื่อ Collection เป็น plotcraft)
        try:
            self.chroma_client = chromadb.HttpClient(
                host=os.environ.get("CHROMA_HOST", "chroma_db"), 
                port=int(os.environ.get("CHROMA_PORT", 8000))
            )
            self.collection = self.chroma_client.get_or_create_collection(name="plotcraft_collection")
            print("✅ RAG Service Initialized for Plotcraft")
        except Exception as e:
            print(f"❌ ChromaDB Error: {e}")
            self.collection = None
    
    # ==================== NOVEL & CHAPTER ====================
    def add_novel_summary_to_rag(self, novel):
        """ จดจำสรุปเนื้อหานิยาย (ชื่อเรื่อง, คำโปรย, หมวดหมู่) """
        try:
            # ใช้ get_FOO_display() เพื่อให้ AI ได้คำเต็มภาษาไทย (เช่น 'แฟนตาซี' แทนที่จะเป็น 'FANTASY')
            content = f"""
            [สรุปข้อมูลนิยาย]
            ชื่อเรื่อง: {novel.title}
            คำโปรย/เรื่องย่อ: {novel.synopsis}
            หมวดหมู่: {novel.get_category_display()}
            ระดับเนื้อหา: {novel.get_rating_display()}
            สถานะ: {novel.get_status_display()}
            """
            
            # ลบข้อมูลเก่าก่อน (ถ้ามี) แล้วค่อยเพิ่มใหม่ กันข้อมูลซ้ำ
            self.delete_data_from_rag(f"novel_{novel.id}")

            self.collection.add(
                documents=[content],
                embeddings=[self.embeddings.embed_query(content)],
                metadatas=[{
                    "type": "novel_summary",
                    "novel_id": str(novel.id),
                    "owner_id": str(novel.author.id)
                }],
                ids=[f"novel_{novel.id}"]
            )
            print(f"✅ RAG Added Novel Summary: {novel.title}")
        except Exception as e:
            print(f"❌ Error adding novel summary: {e}")

    def add_chapter_to_rag(self, chapter):
        """ จดจำเนื้อหาในแต่ละตอน """
        try:
            # ตัดเนื้อหาถ้ายาวเกินไป (Optional) แต่ Gemini รองรับ Context ยาวได้พอสมควร
            content = f"""
            [เนื้อเรื่อง บทที่ {chapter.order}]
            ชื่อตอน: {chapter.title}
            เนื้อหา: {chapter.content}
            """
            
            self.collection.add(
                documents=[content],
                embeddings=[self.embeddings.embed_query(content)],
                metadatas=[{
                    "type": "content",
                    "novel_id": str(chapter.novel.id),
                    "source_id": str(chapter.id),
                    "owner_id": str(chapter.novel.author.id)
                }],
                ids=[f"chap_{chapter.id}"]
            )
            print(f"✅ Added Chapter: {chapter.title}")
        except Exception as e:
             print(f"❌ Error adding chapter: {e}")

    # ==================== CHAT WITH EDITOR ====================

    def chat_with_editor(self, user_query, novel_id=None, user_id=None):
        """ ฟังก์ชันคุยกับพี่บก. (รวมร่าง: คุยเล่น + ตรวจงาน) """
        print(f"💬 Chatting with Editor. Novel ID: {novel_id}, User ID: {user_id}")
        
        context_text = ""
        
        # ค้นหาข้อมูล (ต้องมี User ID เสมอเพื่อความปลอดภัย)
        if user_id: 
            try:
                # ---------------------------------------------------------
                # STEP A: ดึงข้อมูลสรุปนิยาย (Novel Summary) ก่อนเสมอ
                # ---------------------------------------------------------
                if novel_id:
                    summary_results = self.collection.get(
                        where={
                            "$and": [
                                {"type": "novel_summary"},
                                {"novel_id": str(novel_id)}
                            ]
                        },
                        limit=1
                    )
                    if summary_results['documents']:
                        context_text += f"📌 [บริบทหลัก: ข้อมูลนิยาย]\n{summary_results['documents'][0]}\n\n"

                # ---------------------------------------------------------
                # STEP B: ค้นหา Vector (เนื้อหาอื่นๆ ที่ตรงกับคำถาม)
                # ---------------------------------------------------------
                query_vector = self.embeddings.embed_query(user_query)
                
                where_conditions = [{"owner_id": str(user_id)}]
                if novel_id:
                    where_conditions.append({"novel_id": str(novel_id)})
                
                if len(where_conditions) > 1:
                    final_where = {"$and": where_conditions}
                else:
                    final_where = where_conditions[0]

                results = self.collection.query(
                    query_embeddings=[query_vector],
                    n_results=3,
                    where=final_where 
                )
                
                docs = results['documents'][0]
                if docs:
                    context_text = "\n\n".join(docs)
                    print(f"📚 Found {len(docs)} related docs")
                    
            except Exception as e:
                print(f"RAG Error: {e}")

        # 2. สร้าง Prompt เดียว ใช้ด้วยกันทั้งเว็บ
        prompt = f"""
        Role: คุณคือ "พี่บก." (Plotcraft Editor) รุ่นพี่ผู้หญิงที่สนิทกับนักเขียน (User) มาก ๆ
        Personality: 
        - เป็นคนเก่ง ตาไว จับผิดพล็อตเก่งแต่พูดจาถนอมน้ำใจ (Constructive Criticism)
        - ขี้เล่น เป็นกันเอง ให้กำลังใจเก่ง แต่ถ้าเห็นจุดโหว่ของเรื่องต้องรีบทัก
        - มีความรู้เรื่องทฤษฎีการเล่าเรื่อง (Storytelling) แน่นปึ้ก

        บริบทนิยายที่กำลังคุยถึง (Context):
        {context_text if context_text else "ยังไม่มีข้อมูลนิยายเจาะจง ให้คุยเรื่องเทคนิคการเขียนทั่วไป"}

        ข้อความจากน้องนักเขียน: 
        "{user_query}"

        Goals (สิ่งที่ต้องทำ):
        1. วิเคราะห์คำถามของน้องร่วมกับ Context ที่มี
        2. อย่าแค่ตอบรับเฉย ๆ ให้ **"เสนอไอเดียเพิ่ม"** หรือ **"ชวนคิดมุมกลับ"** เสมอ
        3. ถ้า Context มีข้อมูลตัวละคร ให้ยกชื่อตัวละครมาพูดถึงเพื่อให้รู้ว่าพี่อ่านอยู่จริง

        Format (รูปแบบการตอบ):
        - Tone: ภาษาพูด เหมือนพิมพ์แชทไลน์ (แทนตัวว่า "พี่" แทน User ว่า "เรา/น้อง/เตง")
        - Length: 
            - ถ้าคุยเล่น: ตอบสั้นๆ 2-3 ประโยค
            - ถ้าถามงาน/ปรึกษาพล็อต: **ตอบยาวได้ตามความเหมาะสม** แต่ให้เว้นบรรทัดบ่อยๆ ให้อ่านง่าย
        - Style: ห้ามใช้ Markdown หัวข้อใหญ่ๆ (พวก #, *, -) แต่ใช้ Emoji 📌 หรือ 👉 ในการชี้ประเด็นสำคัญได้

        สิ่งต้องห้าม 🚫:
        - ห้ามตอบกว้างๆ แบบ "เขียนดีแล้วค่ะ" โดยไม่บอกว่าดียังไง
        - ห้ามแต่งเรื่องเองมั่วซั่วถ้าไม่มีใน Context (ถ้าไม่รู้ให้ถามน้องกลับ)

        เริ่มตอบน้องเขาได้เลย:
        """
        
        try:
            if self.llm:
                return self.llm.invoke(prompt)
            return "ระบบพี่ยังไม่พร้อมใช้งานค่ะ (No API Key)"
        except Exception as e:
            return f"ขอโทษทีนะ พี่มึนหัวนิดหน่อย (Error: {str(e)})"

        # ==================== CHARACTER ====================

    def generate_character_data(self, concept):
        """ ช่วยคิด/แกะข้อมูลตัวละคร (รองรับทั้งบรีฟสั้นและยาว) """
        
        print(f"🎨 Processing Character Concept: {concept[:50]}...")
        
        try:
            prompt = f"""
            Role: คุณคือผู้ช่วยกรอกแบบฟอร์มตัวละครมืออาชีพ และมีความคิดสร้างสรรค์สูง
            Input: "{concept}"
            
            Instruction:
            1. วิเคราะห์ Input: ถ้ามีข้อมูลอยู่แล้วให้ใช้ตามนั้น ถ้าไม่มีให้ "แต่งเติม" ให้สมบูรณ์และน่าสนใจ
            2. ถ้าไม่มีชื่อ ให้ตั้งชื่อที่เหมาะสมกับธีมเรื่องให้ด้วย
            3. กรอกข้อมูลตัวละครให้ครบถ้วนตามฟิลด์ด้านล่าง
            4. หลีกเลี่ยงการใช้ชื่อ/บทบาท/นิสัยที่ซ้ำซาก จำเจ
            5. หลีกเลี่ยงการใช้ พวก #, *, -, / และตัว , ในการจัดรูปแบบ
            
            Output Format (JSON Only - Keys ต้องตรงตามนี้):
            {{
                "name": "ชื่อเต็มตัวละคร",
                "alias": "ฉายา หรือ ชื่อเล่น",
                "role": "บทบาท (เช่น พระเอก, จอมมาร, ชาวบ้าน)",
                "age": "อายุ (ระบุเป็นตัวเลขหรือช่วงวัย)",
                "birt_date": "วันเกิด",
                "gender": "เพศ",
                "species": "เผ่าพันธุ์",
                "status": "สถานะ (เช่น มีชีวิตอยู่, เสียชีวิต)",
                "occupation": "อาชีพ",
                "appearance": "รูปลักษณ์ภายนอก (บรรยาย หน้าตา การแต่งกาย ส่วนสูง)",
                "personality": "บุคลิกภาพและนิสัย",
                "background": "ภูมิหลังและประวัติโดยย่อ",
                "goals": "เป้าหมายในชีวิต",
                "strengths": "จุดแข็ง",
                "weaknesses": "จุดอ่อน",
                "skills": "ทักษะและความสามารถ",
                "notes": "บันทึกเพิ่มเติม"
            }}
            """
            
            if self.llm:
                response = self.llm.invoke(prompt)
                
                # แกะ JSON (ใช้ Regex กันเหนียวเหมือนเดิม)
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
                else:
                    return json.loads(response)
            
            return None
            
        except Exception as e:
            print(f"Gen Char Error: {e}")
            return None

    def add_character_to_rag(self, char):
        """ จดจำข้อมูลตัวละคร """
        try:
            # สร้างข้อความสรุปตัวละครจาก Field ใน models.py
            content = f"""
            [ข้อมูลตัวละคร]
            ชื่อ: {char.name}
            นามแฝง: {char.alias}
            บทบาท: {char.role}
            นิสัย: {char.personality}
            ปูมหลัง: {char.background}
            จุดแข็ง: {char.strengths}
            จุดอ่อน: {char.weaknesses}
            ทักษะ: {char.skills}
            รูปลักษณ์: {char.appearance}
            อาชีพ: {char.occupation}
            อายุ: {char.age}
            """
            
            self.collection.add(
                documents=[content],
                embeddings=[self.embeddings.embed_query(content)],
                metadatas=[{
                    "type": "character",
                    "novel_id": str(char.project.id) if char.project else "unknown",
                    "owner_id": str(char.created_by.id) if char.created_by else "unknown",
                    "source_id": str(char.id)
                }],
                ids=[f"char_{char.id}"]
            )
            print(f"✅ RAG Added Character: {char.name} (Owner: {char.created_by.id})")
        except Exception as e:
            print(f"❌ Error adding character: {e}")      

    # ==================== LOCATION & ITEM GENERATORS ====================
    
    def generate_location_data(self, concept):
        """ ช่วยคิดข้อมูลสถานที่ (Location) """

        print(f"🎨 Processing Location Concept: {concept[:50]}...")

        try:
            prompt = f"""
            Role: คุณคือผู้ช่วยนักเขียนนิยายแฟนตาซี/ไซไฟมืออาชีพ (World Builder)
            Task: สร้างข้อมูล "สถานที่" (Location) จากคอนเซปต์: "{concept}"
            
            Requirements:
            1. ออกแบบชื่อสถานที่ให้ดูมีมนต์ขลังหรือสมจริงตามบริบท
            2. บรรยายสภาพแวดล้อม (Terrain) และภูมิอากาศ (Climate) ให้เห็นภาพ
            3. เขียนคำบรรยาย (Description) และประวัติความเป็นมา (History/Lore) สั้นๆ
            4. ตอบกลับเป็น JSON Format เท่านั้น โดยใช้ Key ตามนี้:
            {{
                "name": "ชื่อสถานที่",
                "world_type": "เช่น แฟนตาซี, ไซไฟ, โอเมก้าเวิร์ส",
                "region": "ภูมิภาค/อาณาเขตที่ตั้ง",
                "terrain": "ลักษณะภูมิประเทศ (เช่น ภูเขาหิน, ป่าทึบ)",
                "climate": "สภาพอากาศ/บรรยากาศ",
                "description": "คำบรรยายรายละเอียดของสถานที่",
                "history": "ประวัติศาสตร์ความเป็นมา (ถ้ามี)"
                "myths": "ตำนานและเรื่องเล่า",
                "economy": "ระบบเศรษฐกิจ",
                "culture": "วัฒนธรรม ความเชื่อ ศาสนา",
                "language": "ภาษาที่ใช้",
                "ecosystem": "ระบบนิเวศ",
                "politics": "ระบบการการเมืองการปกครอง (เช่น กฎหมาย, ความขัดแย้งทางการเมือง)"
            }}
            """
            
            if self.llm:
                response = self.llm.invoke(prompt)
                
                # แกะ JSON
                try:
                    json_match = re.search(r'\{[\s\S]*\}', response)
                    if json_match:
                        clean_json_str = json_match.group(0)
                        return json.loads(clean_json_str)
                    else:
                        return json.loads(response)
                except:
                    return {"content": response}
            return {"error": "No API Key"}
        except Exception as e:
            print(f"Location Gen Error: {e}")
            return {"error": str(e)}

    def generate_item_data(self, concept):
        """ ช่วยคิดข้อมูลไอเทม (Item) """

        print(f"🎨 Processing Item Concept: {concept[:50]}...")

        try:
            prompt = f"""
            Role: คุณคือผู้ช่วยนักเขียนและนักออกแบบไอเทมในนิยาย
            Task: สร้างข้อมูล "ไอเทม/วัตถุ" (Item) จากคอนเซปต์: "{concept}"
            
            Requirements:
            1. ตั้งชื่อไอเทมให้โดดเด่น
            2. ระบุประเภท (Type) และระดับความหายาก (Rarity) ถ้าจำเป็น
            3. อธิบายคุณสมบัติพิเศษ (Abilities) หรือการใช้งาน
            4. เขียนคำบรรยายรูปลักษณ์และที่มา
            5. ตอบกลับเป็น JSON Format เท่านั้น โดยใช้ Key ตามนี้:
            {{
                "name": "ชื่อไอเทม",
                "abilities": "ความสามารถพิเศษ หรือผลของไอเทม",
                "description": "คำบรรยายรูปลักษณ์และการใช้งาน",
                "history": "ประวัติความเป็นมา ตำนาน",
                "appearance": "ลักษณะภายนอก วัสดุ สี",
                "limitations": "เงื่อนไข ข้อจำกัด หรือผลข้างเคียง",
            }}
            """
            
            if self.llm:
                response = self.llm.invoke(prompt)
                
                # แกะ JSON
                try:
                    json_match = re.search(r'\{[\s\S]*\}', response)
                    if json_match:
                        clean_json_str = json_match.group(0)
                        return json.loads(clean_json_str)
                    else:
                        return json.loads(response)
                except (json.JSONDecodeError, AttributeError):
                    return {"content": response}
            return {"error": "No API Key"}
        except Exception as e:
            print(f"Item Gen Error: {e}")
            return {"error": str(e)}

    def add_location_to_rag(self, location):
        """ จดจำข้อมูลสถานที่ (Location) """
        try:
            # สร้าง Text สำหรับ AI อ่าน (รวมข้อมูลทุกด้าน)
            content = f"""
            [ข้อมูลสถานที่]
            ชื่อ: {location.name}
            ประเภทโลก: {location.world_type}
            
            -- สภาพแวดล้อม --
            ภูมิประเทศ: {location.terrain}
            สภาพอากาศ: {location.climate}
            ระบบนิเวศ: {location.ecosystem}
            
            -- สังคมและวัฒนธรรม --
            การปกครอง: {location.politics}
            เศรษฐกิจ: {location.economy}
            วัฒนธรรม/ความเชื่อ: {location.culture}
            ภาษา: {location.language}
            
            -- ประวัติและตำนาน --
            ประวัติศาสตร์: {location.history}
            ตำนานเรื่องเล่า: {location.myths}
            """
            
            # เตรียม Metadata
            novel_id = str(location.project.id) if location.project else "unknown"
            owner_id = str(location.created_by.id) if location.created_by else "unknown"

            # บันทึกลง ChromaDB
            self.collection.add(
                documents=[content],
                embeddings=[self.embeddings.embed_query(content)],
                metadatas=[{
                    "type": "location",
                    "novel_id": novel_id,
                    "owner_id": owner_id,
                    "source_id": str(location.id)
                }],
                ids=[f"loc_{location.id}"]
            )
            print(f"✅ RAG Added Location: {location.name}")
            
        except Exception as e:
            print(f"❌ Error adding location: {e}")


    def add_item_to_rag(self, item):
        """ จดจำข้อมูลไอเทม (Item) """
        try:
            # ดึงชื่อเจ้าของ/สถานที่เก็บ (ถ้ามี)
            current_owner = item.owner.name if item.owner else "ไม่มีเจ้าของ"
            current_location = item.location.name if item.location else "ไม่ระบุ"
            
            # ใช้ get_category_display() เพื่อดึงคำเต็มจาก Choice (เช่น "Weapon (อาวุธ)")
            category_display = item.get_category_display()

            content = f"""
            [ข้อมูลไอเทม/วัตถุ]
            ชื่อ: {item.name}
            ประเภท: {category_display}
            
            -- คุณสมบัติและเงื่อนไข --
            ความสามารถพิเศษ: {item.abilities}
            ข้อจำกัด/ผลข้างเคียง: {item.limitations}
            
            -- รูปลักษณ์และประวัติ --
            รูปลักษณ์ภายนอก: {item.appearance}
            ประวัติความเป็นมา: {item.history}
            
            -- สถานะปัจจุบัน --
            ผู้ครอบครอง: {current_owner}
            สถานที่เก็บ: {current_location}
            """
            
            novel_id = str(item.project.id) if item.project else "unknown"
            owner_id = str(item.created_by.id) if item.created_by else "unknown"

            self.collection.add(
                documents=[content],
                embeddings=[self.embeddings.embed_query(content)],
                metadatas=[{
                    "type": "item",
                    "novel_id": novel_id,
                    "owner_id": owner_id,
                    "source_id": str(item.id)
                }],
                ids=[f"item_{item.id}"]
            )
            print(f"✅ RAG Added Item: {item.name}")
            
        except Exception as e:
            print(f"❌ Error adding item: {e}")



    # ==================== SCENE DRAFTER ====================       
    
    def generate_scene_draft(self, scene, instruction=""):
        """ ฟังก์ชันสำหรับช่วยร่างฉากนิยาย (Scene Drafter) """
        print(f"✍️ Drafting Scene: {scene.title}")
        
        try:
            # 1. เตรียมข้อมูลวัตถุดิบ (Raw Data)
            pov_name = scene.pov_character.name if scene.pov_character else "ไม่ระบุ"
            pov_desc = f"นิสัย: {scene.pov_character.personality}, รูปลักษณ์: {scene.pov_character.appearance}" if scene.pov_character else ""
            loc_name = scene.location.name if scene.location else "ไม่ระบุ"
            loc_desc = f"สภาพแวดล้อม: {scene.location.terrain}, บรรยากาศ: {scene.location.climate}" if scene.location else ""
            other_chars = ", ".join([c.name for c in scene.characters.all()]) or "ไม่มี"

            # 2. สร้าง Prompt สำหรับนักเขียนเงา
            prompt = f"""
            Role: คุณคือผู้ช่วยนักเขียนมืออาชีพ
            Task: วิเคราะห์คำสั่ง (Instruction) แล้วสร้าง "โครงสร้างฉาก" และ "เนื้อหาร่าง"
            
            🏗️ โครงสร้างฉาก (Scene Structure):
            - ชื่อฉาก: {scene.title}
            - ตัวละครดำเนินเรื่อง (POV): {pov_name} ({pov_desc})
            - สถานที่: {loc_name} ({loc_desc})
            - ตัวละครอื่น ๆ ในฉาก: {other_chars}
            
            🎯 เป้าหมายของฉาก (Goal): {scene.goal}
            🚧 อุปสรรค/ความขัดแย้ง (Conflict): {scene.conflict}
            🏁 ผลลัพธ์ของฉาก (Outcome): {scene.outcome}

            คำสั่ง/ไอเดียจากนักเขียน: "{instruction}"

            📝 คำสั่งการเขียน:
            1. เขียนบรรยายในรูปแบบ "นิยาย" (Narrative) มุมมองบุคคลที่ 3 (หรือ 1 ตามความเหมาะสมของ POV)
            2. เริ่มต้นด้วยการบรรยายบรรยากาศสถานที่ (Setting the scene) ให้เห็นภาพ
            3. ใส่บทพูด (Dialogue) และการกระทำ (Action) ที่สะท้อนนิสัยตัวละคร
            4. ดำเนินเรื่องให้เห็น "อุปสรรค" ที่ตัวละครต้องเจอ และจบลงที่ "ผลลัพธ์" ตามที่ระบุ
            5. ไม่ต้องเขียนยาวมาก เอาแค่โครงร่างหลักๆ ประมาณ 300-500 คำ เพื่อให้นักเขียนไปเกลาต่อได้
            6. ใช้ภาษาไทยสละสลวย เหมาะกับการเป็นนิยาย
            7. **สำคัญมาก**: ตอบกลับเป็น JSON Format เท่านั้น โดยใช้ Key ดังนี้:
               - "goal": (ข้อความบรรยาย ไม่ยาวมาก และไม่สั้นเกินไป)
               - "conflict": (ข้อความบรรยาย ไม่ยาวมาก และไม่สั้นเกินไป)
               - "outcome": (ข้อความบรรยาย ไม่ยาวมาก และไม่สั้นเกินไป)
               - "content": (เนื้อหาบรรยายฉาก)
            8. ถ้ามี POV ให้ใช้มุมมอง เสียง และแทนใช้เป็นชื่อของตัวละคร POV นั้นในการบรรยาย แต่ถ้ายังไม่มีให้แทนเป็นอย่างอื่่นตามความเหมาะสม
            
            ตัวอย่างการตอบ (JSON):
            {{
                "goal": "ตัวเอกต้องการขโมยกุญแจ...",
                "conflict": "ยามเฝ้าอยู่หน้าประตู...",
                "outcome": "ขโมยสำเร็จแต่ถูกจำหน้าได้...",
                "content": "เสียงฝีเท้าเบาหวิว..."
            }}
            
            เริ่มร่างเนื้อหา:
            """
            
            if self.llm:
                response = self.llm.invoke(prompt)
                
                #จุดแก้ที่สำคัญ: การแกะ Clean JSON
                try:
                    # ใช้ Regex ค้นหาเฉพาะส่วนที่เป็น { ... } (เผื่อ AI เผลอใส่ ```json มา)
                    json_match = re.search(r'\{[\s\S]*\}', response) # [\s\S]* หมายถึงเอาทุกตัวอักษรรวมถึงบรรทัดใหม่
                    
                    if json_match:
                        clean_json_str = json_match.group(0)
                        return json.loads(clean_json_str) # ส่งกลับเป็น Python Dict (Object)
                    else:
                        # ถ้าหา JSON ไม่เจอจริงๆ ให้ลอง loads ตรงๆ
                        return json.loads(response)
                        
                except (json.JSONDecodeError, AttributeError):
                    # ถ้าแกะไม่ได้จริง ๆ ให้ส่งเป็น content ล้วน (กัน Error)
                    return {"content": response}

            return {"error": "ระบบยังไม่พร้อมใช้งาน (No API Key)"}
            
        except Exception as e:
            print(f"Draft Error: {e}")
            return f"เกิดข้อผิดพลาดในการร่าง: {str(e)}"
        
        
    def add_scene_to_rag(self, scene):
        """ จดจำข้อมูลโครงสร้างฉาก (Goal, Conflict, Outcome) """
        try:
            # 1. เตรียมข้อมูลให้ AI อ่านง่าย
            pov = scene.pov_character.name if scene.pov_character else "ไม่ระบุ"
            loc = scene.location.name if scene.location else "ไม่ระบุ"
            chars = ", ".join([c.name for c in scene.characters.all()]) or "-"
            
            content = f"""
            [ข้อมูลฉาก]
            ชื่อฉาก: {scene.title} (ลำดับที่ {scene.order})
            สถานะ: {scene.get_status_display()}
            สถานที่: {loc}
            ตัวละครดำเนินเรื่อง (POV): {pov}
            ตัวละครประกอบ: {chars}
            
            🎯 เป้าหมาย (Goal): {scene.goal}
            🚧 อุปสรรค (Conflict): {scene.conflict}
            🏁 ผลลัพธ์ (Outcome): {scene.outcome}
            
            📝 เนื้อหาบางส่วน:
            {scene.content[:1000] if scene.content else "ยังไม่มีเนื้อหา"}
            """
            
            # 2. บันทึกลง ChromaDB
            self.collection.add(
                documents=[content],
                embeddings=[self.embeddings.embed_query(content)],
                metadatas=[{
                    "type": "scene",
                    "novel_id": str(scene.project.id) if scene.project else "unknown",
                    "owner_id": str(scene.created_by.id) if scene.created_by else "unknown",
                    "source_id": str(scene.id)
                }],
                ids=[f"scene_{scene.id}"]
            )
            print(f"✅ RAG Added Scene: {scene.title}")
            
        except Exception as e:
            print(f"❌ Error adding scene: {e}")
        
    def delete_data_from_rag(self, doc_id):
        """ ฟังก์ชันลบข้อมูลออกจากสมอง AI """
        try:
            self.collection.delete(ids=[doc_id])
            print(f"🗑️ Deleted from RAG: {doc_id}")
        except Exception as e:
            print(f"❌ Error deleting from RAG: {e}")
# สร้าง Instance รอไว้เรียกใช้
rag_service = RAGService()