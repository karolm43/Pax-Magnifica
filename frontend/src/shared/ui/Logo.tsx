import { useNavigate } from "react-router-dom";
import styles from "./Logo.module.css";

/**
 * App wordmark in the header (top-left). Styled like the main-menu logo
 * (Ambroise Firmin + TI4 gradient); clicking it returns to the main menu.
 */
function Logo() {
  const navigate = useNavigate();
  return (
    <span
      role="link"
      tabIndex={0}
      className={styles.logo}
      onClick={() => navigate("/")}
      onKeyDown={(e) => {
        if (e.key === "Enter") navigate("/");
      }}
      title="Main menu"
    >
      Custodian Engine
    </span>
  );
}

export default Logo;
