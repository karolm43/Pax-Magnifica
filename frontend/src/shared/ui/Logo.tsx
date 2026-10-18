import { Text } from "@/ds";
import { useNavigate } from "react-router-dom";

/**
 * Znak słowny aplikacji w nagłówku (lewy górny róg). Custodian Engine zastępuje
 * oryginalny baner AsyncTI4 — nie mamy własnej grafiki, więc render tekstowy.
 */
function Logo() {
  const navigate = useNavigate();
  return (
    <Text
      component="span"
      onClick={() => navigate("/")}
      style={{
        cursor: "pointer",
        fontWeight: 700,
        letterSpacing: "0.08em",
        whiteSpace: "nowrap",
        fontSize: 16,
        lineHeight: 1,
      }}
    >
      CUSTODIAN ENGINE
    </Text>
  );
}

export default Logo;
