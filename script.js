document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("menuToggle");
  const nav = document.getElementById("mainNav");
  if (toggle && nav) toggle.addEventListener("click", () => nav.classList.toggle("open"));

  const role = document.getElementById("roleSelect");
  const invite = document.getElementById("inviteField");
  function updateInvite() {
    if (role && invite) invite.classList.toggle("hidden", role.value !== "board");
  }
  if (role) {
    role.addEventListener("change", updateInvite);
    updateInvite();
  }

  document.querySelectorAll(".flash").forEach((item) => {
    setTimeout(() => item.classList.add("fade"), 5000);
  });
});