// utils/auth.js
import axios from "axios";

export const fetchCurrentUser = async () => {
  try {
    const token = localStorage.getItem("token");
    if (!token) return null;

    const res = await axios.get("http://localhost:8000/users/me", {
      headers: { Authorization: `Bearer ${token}` },
    });

    const user = res.data;
    localStorage.setItem("userId", user.id); // store for future use
    localStorage.setItem("email", user.email);
    return user;
  } catch (err) {
    console.error("Failed to fetch current user:", err);
    return null;
  }
};

export const requireLogin = async (navigate) => {
  const userId = localStorage.getItem("userId");
  if (!userId) {
    const user = await fetchCurrentUser();
    if (!user) {
      navigate("/login");
      return null;
    }
    return user.id;
  }
  return parseInt(userId, 10);
};
