import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/react';
import styles from './CollapsibleUnchanged.module.scss';
import ChevronDown from '~icons/custom/chevron-down';
import Icon from '../../ui/Icon/Icon';
import StatusDetails from '../../../tasks/StatusDetails/StatusDetails';

interface Paragraph {
  before: string;
  after: string;
  status: 'CHANGED' | 'UNCHANGED' | 'REJECTED' | 'SKIPPED' | 'ERRORED';
  status_details: string;
}

interface CollapsibleUnchangedProps {
  paragraphs: Paragraph[];
}

const CollapsibleUnchanged: React.FC<CollapsibleUnchangedProps> = ({ paragraphs }) => {
  if (paragraphs.length === 0) {
    return null;
  }

  return (
    <Disclosure as="div" className={styles.container} defaultOpen={false}>
      {({ open }) => (
        <>
          <DisclosureButton className={`${styles.toggleButton} ${styles.toggleContainer} ${open ? styles.expanded : ''}`}>
            <span className={styles.toggleText}>
              {open ? 'Hide' : 'Show'} {paragraphs.length} unchanged paragraph{paragraphs.length > 1 ? 's' : ''}
            </span>
            <Icon
              icon={ChevronDown}
              size={16}
              color="tertiary"
              className={`${styles.toggleIcon} ${open ? styles.expanded : ''}`}
            />
          </DisclosureButton>
          <DisclosurePanel className={styles.content}>
            {paragraphs.map((paragraph, index) => (
              <div key={index} className={styles.paragraphContainer}>
                <p className={styles.paragraph}>
                  {paragraph.before}
                </p>
                <StatusDetails
                  status={paragraph.status}
                  statusDetails={paragraph.status_details}
                  className={styles.statusButton}
                />
              </div>
            ))}
          </DisclosurePanel>
        </>
      )}
    </Disclosure>
  );
};

export default CollapsibleUnchanged;
