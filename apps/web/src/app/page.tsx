import { redirect } from "next/navigation";

// Root halaman → redirect ke /chat (atau /login jika belum auth)
export default function Home() {
  redirect("/chat");
}
