import streamlit as st
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

# ページ設定
st.set_page_config(page_title="シーン生成アプリ", layout="wide")

def init_session_state():
    if "generated_scenes" not in st.session_state:
        st.session_state.generated_scenes = []
    if "selected_scenes" not in st.session_state:
        st.session_state.selected_scenes = []
    if "scene_structure" not in st.session_state:
        st.session_state.scene_structure = {}
    if "generated_scripts" not in st.session_state:
        st.session_state.generated_scripts = []

def create_llm(api_key):
    return ChatAnthropic(
        anthropic_api_key=api_key,
        model="claude-3-5-sonnet-20241022",
        temperature=0.7,
        max_tokens=4000
    )

def parse_scenes(raw_output):
    """生成されたシーンをメインアイデアと詳細アイデアに分解"""
    scene_structure = {}
    current_main = None
    sub_ideas = []
    
    try:
        lines = raw_output.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('■'):
                # 新しいメインアイデアの開始
                if current_main and sub_ideas:
                    # 前のメインアイデアのサブアイデアを保存
                    scene_structure[current_main] = sub_ideas[:10]  # 最大10個まで
                current_main = line.strip()
                sub_ideas = []
            elif current_main and line and not line.startswith('【') and not line.startswith('---'):
                # サブアイデアの追加（直接展開と継続展開は除外）
                if not any(marker in line for marker in ['直接展開', '継続展開', '展開例']):
                    sub_ideas.append(line.strip())
        
        # 最後のメインアイデアのサブアイデアを保存
        if current_main and sub_ideas:
            scene_structure[current_main] = sub_ideas[:10]  # 最大10個まで
            
        return scene_structure
    except Exception as e:
        st.error(f"シーンの解析中にエラーが発生しました: {str(e)}")
        return {}

def display_scene_selection():
    selected_scenes = []
    
    for main_idea, sub_ideas in st.session_state.scene_structure.items():
        with st.expander(main_idea, expanded=True):
            st.write("#### サブアイデア:")
            for i, sub_idea in enumerate(sub_ideas, 1):
                if st.checkbox(f"{i}. {sub_idea}", key=f"{main_idea}_{i}"):
                    selected_scenes.append({
                        'main_idea': main_idea,
                        'sub_idea': sub_idea
                    })
    
    return selected_scenes

def generate_scenes(llm, situation, system_prompt):
    chain = LLMChain(llm=llm, prompt=ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", situation)
    ]))
    return chain.run(situation=situation)

def generate_script(llm, scene, system_prompt):
    chain = LLMChain(llm=llm, prompt=ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", scene)
    ]))
    return chain.run(scene=scene)

def main():
    init_session_state()
    
    st.title("出会いシーン生成アプリ")
    
    with st.sidebar:
        st.header("設定")
        api_key = st.text_input("Anthropic APIキーを入力してください:", type="password")
        
        with st.expander("システムプロンプトの設定", expanded=False):
            scene_system_prompt = st.text_area(
                "シーン生成用システムプロンプト",
                height=300,
                value=st.session_state.get('scene_system_prompt', '')
            )
            script_system_prompt = st.text_area(
                "台本生成用システムプロンプト",
                height=300,
                value=st.session_state.get('script_system_prompt', '')
            )
            
            if st.button("プロンプトを保存"):
                st.session_state['scene_system_prompt'] = scene_system_prompt
                st.session_state['script_system_prompt'] = script_system_prompt
                st.success("プロンプトが保存されました！")
    
    if not api_key:
        st.warning("サイドバーでAPIキーを入力してください")
        return
    
    tab1, tab2, tab3 = st.tabs(["シーン生成", "シーン選択", "台本出力"])
    
    with tab1:
        st.header("シーン生成")
        situation = st.text_area("シチュエーションを入力してください:", height=100)
        
        if st.button("シーンを生成", type="primary") and situation:
            with st.spinner("シーンを生成中..."):
                try:
                    llm = create_llm(api_key)
                    raw_scenes = generate_scenes(llm, situation, scene_system_prompt)
                    st.session_state.scene_structure = parse_scenes(raw_scenes)
                    st.success("シーンが生成されました！")
                    
                    for main_idea, sub_ideas in st.session_state.scene_structure.items():
                        with st.expander(main_idea, expanded=True):
                            for i, sub_idea in enumerate(sub_ideas, 1):
                                st.write(f"{i}. {sub_idea}")
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
    
    with tab2:
        st.header("シーン選択")
        if st.session_state.scene_structure:
            st.session_state.selected_scenes = display_scene_selection()
            
            if st.session_state.selected_scenes:
                st.write("### 選択されたシーン:")
                for scene in st.session_state.selected_scenes:
                    st.write(f"- {scene['sub_idea']}")
                
                if st.button("選択したシーンの台本を生成", type="primary"):
                    with st.spinner("台本を生成中..."):
                        try:
                            llm = create_llm(api_key)
                            st.session_state.generated_scripts = []
                            for scene_info in st.session_state.selected_scenes:
                                script = generate_script(llm, scene_info['sub_idea'], script_system_prompt)
                                st.session_state.generated_scripts.append({
                                    'main_idea': scene_info['main_idea'],
                                    'sub_idea': scene_info['sub_idea'],
                                    'script': script
                                })
                            st.success("台本が生成されました！")
                        except Exception as e:
                            st.error(f"エラーが発生しました: {str(e)}")
        else:
            st.info("先にシーンを生成してください。")
    
    with tab3:
        st.header("生成された台本")
        if st.session_state.generated_scripts:
            for script_info in st.session_state.generated_scripts:
                with st.expander(f"台本: {script_info['sub_idea']}", expanded=True):
                    st.write("#### メインアイデア:")
                    st.write(script_info['main_idea'])
                    st.write("#### 選択されたシーン:")
                    st.write(script_info['sub_idea'])
                    st.write("#### 台本:")
                    st.write(script_info['script'])
                    st.divider()
        else:
            st.info("台本はまだ生成されていません。シーンを選択して台本を生成してください。")

if __name__ == "__main__":
    main() 