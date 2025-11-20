const alertBox = document.getElementById("profile-alert");
const photoImg = document.getElementById("profile-photo");
const noPhotoText = document.getElementById("no-photo");

const nameInput = document.getElementById("name");
const infoInput = document.getElementById("info");
const softSkillsInput = document.getElementById("soft_skills");

const photoInput = document.getElementById("photo-input");
const uploadBtn = document.getElementById("btn-upload-photo");
const form = document.getElementById("profile-form");

function showAlert(kind, message) {
  alertBox.className = `alert alert-${kind}`;
  alertBox.textContent = message;
  alertBox.classList.remove("d-none");
}

function hideAlert() {
  alertBox.classList.add("d-none");
}

// Load profile on page load
async function loadProfile() {
  hideAlert();
  try {
    const res = await fetch("/api/profile");
    if (!res.ok) {
      showAlert("danger", `Error loading profile (${res.status})`);
      return;
    }
    const data = await res.json();
    nameInput.value = data.name || "";
    infoInput.value = data.info || "";
    softSkillsInput.value = data.soft_skills || "";

    if (data.photo_path) {
      photoImg.src = `/static/${data.photo_path}`;
      photoImg.style.display = "block";
      noPhotoText.style.display = "none";
    } else {
      photoImg.style.display = "none";
      noPhotoText.style.display = "block";
    }
  } catch (err) {
    console.error(err);
    showAlert("danger", "Network error while loading profile.");
  }
}

// Save profile text fields
async function saveProfile(evt) {
  evt.preventDefault();
  hideAlert();

  const payload = {
    name: nameInput.value.trim(),
    info: infoInput.value.trim(),
    soft_skills: softSkillsInput.value.trim()
  };

  try {
    const res = await fetch("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      showAlert("danger", `Error saving profile (${res.status})`);
      return;
    }

    await res.json();
    showAlert("success", "Profile saved.");
  } catch (err) {
    console.error(err);
    showAlert("danger", "Network error while saving profile.");
  }
}

// Upload photo and refresh view
async function uploadPhoto() {
  hideAlert();
  const file = photoInput.files[0];
  if (!file) {
    showAlert("warning", "Please select a photo first.");
    return;
  }

  const formData = new FormData();
  formData.append("photo", file);

  try {
    const res = await fetch("/api/profile/photo", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const text = await res.text();
      console.error(text);
      showAlert("danger", `Error uploading photo (${res.status}).`);
      return;
    }

    const data = await res.json();
    if (data.photo_path) {
      photoImg.src = `/static/${data.photo_path}`;
      photoImg.style.display = "block";
      noPhotoText.style.display = "none";
    }
    showAlert("success", "Photo uploaded.");
  } catch (err) {
    console.error(err);
    showAlert("danger", "Network error while uploading photo.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadProfile();
  form.addEventListener("submit", saveProfile);
  uploadBtn.addEventListener("click", (e) => {
    e.preventDefault();
    uploadPhoto();
  });
});
