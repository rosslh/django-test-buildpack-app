import React, { useState } from 'react';
import Info from '~icons/custom/info';
import IconButton from '../../shared/ui/IconButton/IconButton';
import Modal from '../../shared/components/Modal/Modal';
import styles from './StatusDetails.module.scss';

interface StatusDetailsProps {
  status: 'CHANGED' | 'UNCHANGED' | 'REJECTED' | 'SKIPPED' | 'ERRORED';
  statusDetails: string;
  className?: string;
}

const StatusDetails: React.FC<StatusDetailsProps> = ({ status, statusDetails, className }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'CHANGED':
        return 'Changed';
      case 'UNCHANGED':
        return 'Unchanged';
      case 'REJECTED':
        return 'Rejected';
      case 'SKIPPED':
        return 'Skipped';
      case 'ERRORED':
        return 'Error';
      default:
        return status;
    }
  };

  return (
    <>
      <IconButton
        icon={Info}
        onClick={handleOpenModal}
        size={16}
        color="tertiary"
        aria-label={`View ${getStatusLabel(status).toLowerCase()} status details`}
        title={`View ${getStatusLabel(status).toLowerCase()} status details`}
        className={className}
      />

      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title="Paragraph Status Details"
        primaryButton={{}}
      >
        <div className={styles.content}>
          <div className={styles.statusRow}>
            <span className={styles.label}>Status:</span>
            <span className={`${styles.status} ${styles[status.toLowerCase()]}`}>
              {getStatusLabel(status)}
            </span>
          </div>
          <div className={styles.detailsRow}>
            <span className={styles.label}>Details:</span>
            <span className={styles.details}>{statusDetails}</span>
          </div>
        </div>
      </Modal>
    </>
  );
};

export default StatusDetails;
