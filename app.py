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
    
    try:
        lines = raw_output.split('\n')
        for line in lines:
            if line.startswith('■'):
                current_main = line.strip()
                scene_structure[current_main] = []
            elif current_main and line.strip() and not line.startswith('■'):
                cleaned_line = ' '.join(line.split()[1:]) if line.split()[0].isdigit() else line
                scene_structure[current_main].append(cleaned_line.strip())
        return scene_structure
    except Exception as e:
        st.error(f"シーンの解析中にエラーが発生しました: {str(e)}")
        return {}

def display_scene_selection():
    """シーン選択UIの表示"""
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
    """シーンの生成"""
    scene_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", f"以下の状況で出会いのシーンを生成してください：\n{situation}")
    ])
    
    chain = LLMChain(llm=llm, prompt=scene_prompt)
    return chain.run(situation=situation)

def generate_script(llm, scene, system_prompt):
    """台本の生成"""
    script_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", f"以下のシーンを台本形式で書いてください：\n{scene}")
    ])
    
    chain = LLMChain(llm=llm, prompt=script_prompt)
    return chain.run(scene=scene)

def main():
    init_session_state()
    
    st.title("出会いシーン生成アプリ")
    
    # サイドバーの設定
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
    
    # タブの作成
    tab1, tab2, tab3 = st.tabs(["シーン生成", "シーン選択", "台本出力"])
    
    # タブ1: シーン生成
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
                    
                    # 生成されたシーンの表示
                    for main_idea, sub_ideas in st.session_state.scene_structure.items():
                        with st.expander(main_idea, expanded=True):
                            for i, sub_idea in enumerate(sub_ideas, 1):
                                st.write(f"{i}. {sub_idea}")
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
    
    # タブ2: シーン選択
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
    
    # タブ3: 台本出力
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