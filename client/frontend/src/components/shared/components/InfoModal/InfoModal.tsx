import Modal from "../Modal/Modal";
import { API_KEY_GUIDES } from "../../../../constants/apiKeyGuides";
import styles from "./InfoModal.module.scss";
import Linkify from "react-linkify";

interface InfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  provider: string;
}

function InfoModal({ isOpen, onClose, provider }: InfoModalProps) {
  const guide = API_KEY_GUIDES[provider];

  if (!guide) {
    return null;
  }

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title={guide.title}
      primaryButton={{ text: "Got it" }}
    >
      <div className={styles.content}>
        <p className={styles.intro}>Follow these steps to get your API key:</p>
        <ol className={styles.stepsList}>
          {guide.steps.map((step, index) => (
            <li key={index} className={styles.step}>
              <Linkify
                componentDecorator={(
                  decoratedHref: string,
                  decoratedText: string,
                  key: number
                ) => (
                  <a
                    href={decoratedHref}
                    key={key}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {decoratedText}
                  </a>
                )}
              >
                {step}
              </Linkify>
            </li>
          ))}
        </ol>
      </div>
    </Modal>
  );
}

export default InfoModal;
