// Preview wrapper — renders the static dashboard in an iframe so all
// inline scripts execute exactly as they would in the Umbrel nginx container.
// The actual Umbrel deployment serves exports/app/index.html directly via nginx.
export default function Page() {
  return (
    <iframe
      src="/dashboard"
      style={{ width: "100%", height: "100vh", border: "none", display: "block" }}
      title="Project X BCH Solo Dashboard"
    />
  );
}
