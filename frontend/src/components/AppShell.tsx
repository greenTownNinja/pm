"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LoginForm } from "@/components/LoginForm";
import { logout, me, type User } from "@/lib/api";

export const AppShell = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    me()
      .then(setUser)
      .finally(() => setIsLoading(false));
  }, []);

  const handleSignOut = async () => {
    await logout();
    setUser(null);
  };

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-sm uppercase tracking-[0.3em] text-[var(--gray-text)]">
          Loading
        </p>
      </main>
    );
  }

  if (!user) {
    return <LoginForm onSignedIn={setUser} />;
  }

  return <KanbanBoard username={user.username} onSignOut={handleSignOut} />;
};
