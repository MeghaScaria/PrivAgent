"""
Builds research_paper/v2/PrivAgent_v2_DRAFT.md from research_paper/v2/build/manuscript_src.md.

- [@key] citations are numbered in order of first appearance (IEEE style); "[@a], [@b]" stays as "[1], [2]".
- The reference list is written in that order, from REFS below, in place of {{REFERENCES}}.
- Every key cited must be in REFS; REFS entries never cited are reported and left out (IEEE Access asks
  for no references that are not relevant to the work).
- Entries were checked against primary sources; the URL checked for each is in
  research_paper/v2/SUPPLEMENTARY.md (S9, reference verification). Nothing is filled in from memory.

    python research_paper/v2/build/build_manuscript.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "manuscript_src.md")
DST = os.path.join(os.path.dirname(HERE), "PrivAgent_v2_DRAFT.md")

REFS = {
    "mcp_anthropic": 'Anthropic. "Introducing the Model Context Protocol." Nov. 25, 2024. [Online]. Available: https://www.anthropic.com/news/model-context-protocol',
    "mcp_spec": 'Model Context Protocol. "Specification," rev. 2025-06-18. [Online]. Available: https://modelcontextprotocol.io/specification/2025-06-18',
    "langgraph": 'LangChain. "LangGraph: Human-in-the-loop / interrupts." Accessed: Nov. 10, 2026. [Online]. Available: https://docs.langchain.com/oss/python/langgraph/interrupts',
    "greshake": 'K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, "Not what you\'ve signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection," in *Proc. 16th ACM Workshop Artif. Intell. Secur. (AISec)*, 2023, pp. 79–90.',
    "injecagent": 'Q. Zhan, Z. Liang, Z. Ying, and D. Kang, "InjecAgent: Benchmarking indirect prompt injections in tool-integrated large language model agents," in *Findings Assoc. Comput. Linguistics: ACL 2024*, 2024.',
    "agentdojo": 'E. Debenedetti, J. Zhang, M. Balunović, L. Beurer-Kellner, M. Fischer, and F. Tramèr, "AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents," in *Proc. Adv. Neural Inf. Process. Syst. (NeurIPS), Datasets Benchmarks Track*, vol. 37, 2024.',
    "camel": 'E. Debenedetti, I. Shumailov, T. Fan, J. Hayes, N. Carlini, D. Fabian, C. Kern, C. Shi, A. Terzis, and F. Tramèr, "Defeating prompt injections by design," 2025, *arXiv:2503.18813*. **[VERIFY: venue]**',
    "fides": 'M. Costa, B. Köpf, A. Kolluri, A. Paverd, M. Russinovich, A. Salem, S. Tople, L. Wutschitz, and S. Zanella-Béguelin, "Securing AI agents with information-flow control," in *Proc. Adv. Neural Inf. Process. Syst. (NeurIPS)*, 2026.',
    "permissive": 'S. A. Siddiqui, R. Gaonkar, B. Köpf, D. Krueger, A. Paverd, A. Salem, S. Tople, L. Wutschitz, M. Xia, and S. Zanella-Béguelin, "Permissive information-flow analysis for large language models," *Trans. Mach. Learn. Res.*, Oct. 2025.',
    "agate": 'X. Zhang, Z. Cheng, K. Liu, Z. Sun, S. Fan, T. Yuan, B. Yuan, W. Qiang, and D. Zou, "AGATE: Provenance-based runtime defense against compositional attacks on LLM agents," 2026, *arXiv:2609.30830*.',
    "capagent": 'H. Hou, Y. Ma, and J. Miao, "CapAgent: Semantic data-flow governance for LLM agents in big-data cognitive computing," *Big Data Cogn. Comput.*, vol. 10, no. 9, p. 293, Sep. 2026, doi: 10.3390/bdcc10090293.',
    "agentbom": 'C. Li, L. Zhang, J. Zhai, S. Feng, X. Yang, H. Wang, S. Dou, Y. Ji, Y. Hu, Y. Wu, Y. Liu, and D. Zou, "Towards security-auditable LLM agents: A unified graph representation," 2026, *arXiv:2605.06812*.',
    "pcaa": 'Z. Wang, "Proof-carrying agent actions: Model-agnostic runtime governance for heterogeneous agent systems," 2026, *arXiv:2606.04104*.',
    "progent": 'T. Shi, J. He, Z. Wang, H. Li, L. Wu, W. Guo, and D. Song, "Progent: Programmable privilege control for LLM agents," 2025, *arXiv:2504.11703*.',
    "isolategpt": 'Y. Wu, F. Roesner, T. Kohno, N. Zhang, and U. Iqbal, "IsolateGPT: An execution isolation architecture for LLM-based agentic systems," in *Proc. Netw. Distrib. Syst. Secur. Symp. (NDSS)*, 2025.',
    "agentsentry": 'R. Sequeira, S. Damianakis, U. Iqbal, and K. Psounis, "Agent-Sentry: Bounding LLM agents via execution provenance," 2026, *arXiv:2603.22868*.',
    "denning": 'D. E. Denning, "A lattice model of secure information flow," *Commun. ACM*, vol. 19, no. 5, pp. 236–243, 1976.',
    "buneman": 'P. Buneman, S. Khanna, and W.-C. Tan, "Why and where: A characterization of data provenance," in *Proc. Int. Conf. Database Theory (ICDT)*, LNCS 1973, 2001, pp. 316–330.',
    "friedman": 'J. H. Friedman, "Greedy function approximation: A gradient boosting machine," *Ann. Statist.*, vol. 29, no. 5, pp. 1189–1232, 2001.',
    "sklearn": 'F. Pedregosa *et al.*, "Scikit-learn: Machine learning in Python," *J. Mach. Learn. Res.*, vol. 12, pp. 2825–2830, 2011.',
    "kapoor": 'S. Kapoor and A. Narayanan, "Leakage and the reproducibility crisis in machine-learning-based science," *Patterns*, vol. 4, no. 9, art. 100804, 2023.',
    "geirhos": 'R. Geirhos, J.-H. Jacobsen, C. Michaelis, R. Zemel, W. Brendel, M. Bethge, and F. A. Wichmann, "Shortcut learning in deep neural networks," *Nat. Mach. Intell.*, vol. 2, no. 11, pp. 665–673, 2020.',
    "parasuraman": 'R. Parasuraman and V. Riley, "Humans and automation: Use, misuse, disuse, abuse," *Hum. Factors*, vol. 39, no. 2, pp. 230–253, 1997.',
    "wilson": 'E. B. Wilson, "Probable inference, the law of succession, and statistical inference," *J. Amer. Statist. Assoc.*, vol. 22, no. 158, pp. 209–212, 1927.',
    "wangpep": 'S. Wang, S. Zhu, and R. Li, "Runtime policy enforcement for MCP-based LLM agents," *Electronics*, vol. 15, no. 13, art. 2829, Jun. 2026, doi: 10.3390/electronics15132829.',
    "arp": 'D. Arp, E. Quiring, F. Pendlebury, A. Warnecke, F. Pierazzi, C. Wressnegger, L. Cavallaro, and K. Rieck, "Dos and don\'ts of machine learning in computer security," in *Proc. 31st USENIX Secur. Symp. (USENIX Security 22)*, Boston, MA, USA, Aug. 2022, pp. 3971–3988.',
    "tesseract": 'F. Pendlebury, F. Pierazzi, R. Jordaney, J. Kinder, and L. Cavallaro, "TESSERACT: Eliminating experimental bias in malware classification across space and time," in *Proc. 28th USENIX Secur. Symp. (USENIX Security 19)*, Santa Clara, CA, USA, Aug. 2019, pp. 729–746.',
    "agentleak": 'F. El Yagoubi, G. Badu-Marfo, and R. Al Mallah, "AgentLeak: A benchmark for internal-channel privacy leakage in multi-agent LLM systems," *IEEE Access*, vol. 14, pp. 94960–94978, 2026, doi: 10.1109/ACCESS.2026.3704541.',
    "guardagent": 'Z. Xiang, L. Zheng, Y. Li, J. Hong, Q. Li, H. Xie, J. Zhang, Z. Xiong, C. Xie, C. Yang, D. Song, and B. Li, "GuardAgent: Safeguard LLM agents via knowledge-enabled reasoning," in *Proc. 42nd Int. Conf. Mach. Learn. (ICML)*, PMLR, vol. 267, 2025, pp. 68316–68342.',
    "shieldagent": 'Z. Chen, M. Kang, and B. Li, "ShieldAgent: Shielding agents via verifiable safety policy reasoning," in *Proc. 42nd Int. Conf. Mach. Learn. (ICML)*, PMLR, vol. 267, 2025, pp. 8313–8344.',
    "kairos": 'K. Hempel, N. Loose, L. Cavallaro, and T. Eisenbarth, "Kairos: Transactional security enforcement at the system boundary for LLM agents," 2026, *arXiv:2610.18457*.',
    "noumi": 'I. M. Noumi, T. A. Nowshin, M. M. H. Nipu, M. S. Mahmood, M. J. Hossain, and M. F. Mridha, "Agentic security: A systematization of tools, failure modes, and design laws for LLM-driven penetration testing," 2026, *arXiv:2608.21423*.',
    "mcnemar": 'Q. McNemar, "Note on the sampling error of the difference between correlated proportions or percentages," *Psychometrika*, vol. 12, no. 2, pp. 153–157, Jun. 1947, doi: 10.1007/BF02295996.',
    "delong": 'E. R. DeLong, D. M. DeLong, and D. L. Clarke-Pearson, "Comparing the areas under two or more correlated receiver operating characteristic curves: A nonparametric approach," *Biometrics*, vol. 44, no. 3, p. 837, Sep. 1988, doi: 10.2307/2531595. **[VERIFY: end page; Crossref gives the first page only]**',
}

KEY = re.compile(r"\[@([a-z_]+)\]")


def main():
    src = open(SRC, encoding="utf-8").read()
    # strip the source-only header comment (it mentions the [@key] syntax itself)
    src = re.sub(r"\A<!--\nSOURCE of .*?-->\n\n", "", src, flags=re.S)
    body, _, tail = src.partition("{{REFERENCES}}")
    order = []
    for m in KEY.finditer(body):
        if m.group(1) not in REFS:
            sys.exit(f"unknown citation key: {m.group(1)}")
        if m.group(1) not in order:
            order.append(m.group(1))
    num = {k: i + 1 for i, k in enumerate(order)}
    body = KEY.sub(lambda m: f"[{num[m.group(1)]}]", body)
    refs = "\n\n".join(f"[{num[k]}] {REFS[k]}" for k in order)
    note = ("<!-- GENERATED from research_paper/v2/build/manuscript_src.md by build_manuscript.py; "
            "edit the source, not this file. -->\n\n")
    open(DST, "w", encoding="utf-8", newline="\n").write(note + body + refs + tail)
    unused = sorted(set(REFS) - set(order))
    print(f"{len(order)} references cited; not cited (left out): {unused}")
    print("wrote", DST)


if __name__ == "__main__":
    main()
