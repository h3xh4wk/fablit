(() => {
  "use strict";
  const download = (content, filename, type) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  };
  const readJson = (id) => {
    const node = document.getElementById(id);
    if (!node) return null;
    try { return JSON.parse(node.textContent || "null"); } catch { return null; }
  };
  const formatMarkdown = (record) => {
    const lines = [
      "# Practice Log: " + (record.activity_title || "Untitled practice"),
      "**Date:** " + (record.completed_at || ""),
      "**Session ID:** " + (record.activity_id || ""), ""
    ];
    if (record.pre_practice_intention) lines.push("## 1. Pre-Practice Intention", "> " + record.pre_practice_intention, "");
    lines.push("## 2. Submitted Artifact", "", "```", record.learner_response || "", "```", "");
    lines.push("## 3. System Evaluation");
    for (const [label, values] of [["What you noticed", record.strengths], ["What to think about", record.improvements], ["Try this next", record.next_steps]]) {
      if (Array.isArray(values) && values.length) lines.push("- **" + label + ":** " + values.join(" "));
    }
    if (record.feedback) lines.push("- **Feedback:** " + record.feedback);
    lines.push("");
    if (record.reflection) lines.push("## 4. Learner Reflection", "", record.reflection, "");
    return lines.join("\n");
  };
  const session = readJson("fablit-session-export-data");
  document.querySelector(".js-export-session")?.addEventListener("click", () => {
    if (!session) return;
    const timestamp = (session.completed_at || new Date().toISOString()).replace(/[:.]/g, "-");
    download(formatMarkdown(session), "fablit-session-" + (session.activity_id || "practice") + "-" + timestamp + ".md", "text/markdown;charset=utf-8");
  });
  const history = readJson("fablit-history-export-data");
  document.querySelector(".js-export-history")?.addEventListener("click", () => {
    if (!Array.isArray(history)) return;
    const payload = { specVersion: "027", exportedAt: new Date().toISOString(), records: history };
    const date = new Date().toISOString().slice(0, 10);
    download(JSON.stringify(payload, null, 2), "fablit-history-export-private-learner-" + date + ".json", "application/json;charset=utf-8");
  });
})();