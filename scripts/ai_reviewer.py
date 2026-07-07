# scripts/ai_reviewer.py
import os
import subprocess
import sys

from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage


def get_diff(target_branch="origin/main"):
    """Git diff를 가져옵니다."""
    try:
        # fetch를 먼저 수행하여 최신 상태 확인
        subprocess.run(
            ["git", "fetch", "origin", "main"], check=True, capture_output=True
        )

        # diff 생성
        result = subprocess.run(
            ["git", "diff", f"{target_branch}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error getting diff: {e}")
        return None


def main():
    # 1. API 키 확인
    if not os.getenv("UPSTAGE_API_KEY"):
        print("❌ UPSTAGE_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    # 2. Diff 가져오기
    diff = get_diff()
    if not diff:
        print("✅ 변경 사항이 없거나 diff를 가져올 수 없습니다.")
        sys.exit(0)

    # 3. 토큰 제한 (너무 긴 diff는 자름)
    if len(diff) > 10000:
        diff = diff[:10000] + "\n...(truncated)..."

    # 4. LLM 설정 (Solar Mini 활용)
    llm = ChatUpstage(model="solar-mini")

    # 5. 프롬프트 작성
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "당신은 시니어 Python 개발자입니다. 코드 변경사항(diff)을 보고 간단명료하게 리뷰해주세요. 잠재적인 버그나 스타일 문제를 지적하고, 칭찬할 점은 칭찬해주세요. 리뷰는 한국어로 작성하고 마크다운 형식을 사용하세요.",
            ),
            ("human", "다음 코드 변경사항을 리뷰해주세요:\n\n```diff\n{diff}\n```"),
        ]
    )

    # 6. 리뷰 생성
    chain = prompt | llm
    try:
        response = chain.invoke({"diff": diff})
        print(response.content)
    except Exception as e:
        print(f"❌ 리뷰 생성 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
