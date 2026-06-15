import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();

    // Simulação de login (podes substituir por API depois)
    if (email && senha) {
      navigate("/dashboard"); // 👈 redireciona
    }
  };

  return (
    <div className="h-screen flex items-center justify-center bg-[#0d1117] text-white">
      <div className="bg-[#161b22] p-8 rounded-xl w-[350px] shadow-lg">

        <div className="text-center mb-4">
          <h1 className="text-lg font-semibold">📊 Sistema de Requisitos</h1>
          <p className="text-sm text-gray-400">
            Faça login para continuar
          </p>
        </div>

        <form onSubmit={handleLogin}>
          <input
            type="email"
            placeholder="Email"
            className="w-full p-2 mb-3 bg-[#0d1117] border border-gray-700 rounded"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <input
            type="password"
            placeholder="Senha"
            className="w-full p-2 mb-4 bg-[#0d1117] border border-gray-700 rounded"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />

          <button className="w-full bg-green-600 p-2 rounded">
            Entrar
          </button>
        </form>

      </div>
    </div>
  );
}