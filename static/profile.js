"use strict";
(async () => {
  try {
    const username = location.pathname.split("/").filter(Boolean).at(-1);
    const response = await fetch(`/api/public/${encodeURIComponent(username)}`);
    if (!response.ok)
      throw new Error("This profile is private or does not exist.");
    const data = await response.json();
    document.getElementById("name").textContent = `${data.username}'s reading`;
    for (const [label, key] of [
      ["Characters", "total_chars"],
      ["Reading days", "reading_days"],
      ["Reading streak", "reading_streak"],
      ["Goal streak", "goal_streak"],
    ]) {
      const item = document.createElement("div"),
        caption = document.createElement("span"),
        number = document.createElement("strong");
      caption.textContent = label;
      number.textContent = new Intl.NumberFormat().format(data[key]);
      item.append(caption, number);
      document.getElementById("public-stats").append(item);
    }
  } catch (error) {
    document.getElementById("message").textContent = error.message;
  }
})();
