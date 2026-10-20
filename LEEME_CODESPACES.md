# OMNIA ONLINE O1-CS — Relay en GitHub Codespaces

## Qué requiere

- Un Codespace encendido con Python 3.10+ y el puerto público **27862**.
- Unity OMNIA **E5.25 + ONLINE O1-CS** compilado en los dos PC.
- Los dos jugadores deben tener un mazo **ACTIVO y VÁLIDO** en el constructor.
- No hace falta Tailscale, IP pública, abrir el router ni contratar un VPS.
- GitHub Codespaces es infraestructura externa de GitHub que ya utilizas. El relay no se aloja en los PC de los jugadores.

## 1. Iniciar el relay en Codespaces

Sube únicamente la carpeta `OMNIA_CODESPACES_RELAY` al Codespace (puede estar junto a Forja, en directorio distinto).

```bash
cd OMNIA_CODESPACES_RELAY
python3 -m pip install --user -r requirements.txt
python3 -m unittest -v test_codespaces_relay.py
python3 omnia_codespaces_relay.py --host 127.0.0.1 --port 27862
```

No se modifica el puerto 8000/8080 de Forja ni se utiliza su base de datos.

En la pestaña **PORTS** de Codespaces:

1. `Add port` → `27862`.
2. `Port Visibility` → **Public** (si GitHub permite puertos públicos en tu cuenta/organización).
3. Mantén el **Port Protocol en HTTP** dentro de Codespaces. GitHub expone una **URL HTTPS** al exterior y termina TLS en el proxy; cambiar el protocolo interno a HTTPS puede volver a poner el puerto en privado.
4. Copia la **URL HTTPS completa** de ese puerto, por ejemplo `https://NOMBRE-CODESPACE-27862.app.github.dev`.
5. Si reinicias Codespaces o vuelves a reenviar el puerto, revisa de nuevo la visibilidad: podría volver a privada.

No es necesario un certificado PEM ni configurar TLS en Python.

## 2. Construir OMNIA y entrar

- Instala el parche ONLINE O1-CS **sobre el E5.25 que pasó SelfTests**. **No instales el O1/TLS anterior**.
- Abre Unity 6000.4.0f1 y comprueba compilación normal.
- Ejecuta el SelfTest de ONLINE O1-CS; luego genera una build Windows completa.
- El Host y el Cliente deben usar **TCP lógico 7 / BOARD 17**.
- Ambos abren OMNIA con `-omniaMP2` (o el panel F8 habilitado desde Unity).
- Ambos pegan la misma URL `https://...app.github.dev` en **ONLINE O1-CS**.
- Host pulsa **Crear sala privada** y envía el código de 12 caracteres.
- Cliente pega ese código y pulsa **Unirse con código**.
- Cuando el Cliente se autentica, transmite su mazo activo al Host y espera el acuse.
- Host verá **Mazo del colaborador validado: SI** y recién entonces abre el duelo real.
- El Host utiliza su propio mazo activo; el Cliente su propio mazo activo, cada uno con su Santuario.

## 3. Resguardo, límites y soluciones

- La URL Codespaces y el código deben compartirse solo con el colaborador. **El puerto Public es accesible por terceros**; el código de sala es el secreto de unión. No constituye seguridad de servicio público de producción.
- El relay transporta texto MP2 entre solo dos conexiones y NO ejecuta habilidades. Sigue habiendo un Host autoritativo.
- Solo se admiten salas privadas. Sin lista pública ni emparejamiento.
- El relay conserva una sala esperando 15 minutos sin colaborador. Tras ese plazo hay que crear otra.
- Si el Codespace entra en reposo, se pierde el relay y la partida. Este sistema está destinado a pruebas.
- Si `JOIN` no funciona, comprueba que el puerto está **Public**, que el proceso Python sigue en ejecución y que el código coincide.
- Si hay incompatibilidad de contrato, recompila AMBAS builds con el mismo parche.
- Si aparece error de mazo: activa en el constructor un mazo legal de 40 cartas + 1 Santuario en cada computador; sincroniza los catálogos/cards.json de las builds.
- No envíes ni configures tokens de GitHub en OMNIA.
- La privacidad de información del duelo depende también del contrato MP2. El relay no almacena el historial, pero el tráfico pasa por Codespaces y su proxy.
- Solo se realizaron pruebas automatizadas reales del relay en loopback. **No hay certificación WAN de dos builds ni compilación Unity desde esta entrega.**

## 4. Compatibilidad LAN

La ruta original de Host/Cliente por TCP LAN continúa disponible en F8. Si no deseas Codespaces para una sesión, puedes mantener las pruebas LAN de siempre.
