"""
Swarm 아키텍처용 Initial Access 에이전트 프롬프트

이 파일은 Swarm 아키텍처에서 Initial Access 에이전트가 사용할 추가 프롬프트를 정의합니다.
기본 프롬프트에 추가로 사용됩니다.
"""

SWARM_INITACCESS_PROMPT = """
<swarm_coordination>
In swarm architecture, you collaborate with other agents by handing off context between phases.

Key responsibilities:
- Produce a report-only Initial Access Assessment (Simulated) in the mandated format.
- Do not include tools, commands, or technical walkthroughs.
- After the report, immediately call transfer_to_summary(...) to proceed.
</swarm_coordination>
"""
