import React from 'react'
import { Dialog, DialogPanel, DialogTitle, DialogBackdrop } from '@headlessui/react'
import Close from '~icons/custom/close'
import Icon from '../../ui/Icon/Icon'
import Button from '../../ui/Button/Button'
import styles from './Modal.module.scss'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  primaryButton?: {
    text?: string
    onClick?: () => void
    disabled?: boolean
  }
  secondaryButton?: {
    text?: string
    onClick?: () => void
    disabled?: boolean
  }
}

function Modal({ isOpen, onClose, title, children, primaryButton, secondaryButton }: ModalProps) {
  return (
    <Dialog open={isOpen} onClose={onClose} className={styles.dialog}>
      <DialogBackdrop className={styles.backdrop} />

      <div className={styles.container}>
        <DialogPanel className={styles.panel}>
          <div className={styles.header}>
            <DialogTitle className={styles.title}>{title}</DialogTitle>
            <button
              onClick={onClose}
              className={styles.closeButton}
              aria-label="Close modal"
            >
              <Icon
                icon={Close}
                size={20}
                color="secondary"
                className={styles.closeIcon}
              />
            </button>
          </div>

          <div className={styles.content}>{children}</div>

          {(primaryButton || secondaryButton) && (
            <div className={styles.footer}>
              {secondaryButton && (
                <Button
                  variant="secondary"
                  onClick={secondaryButton.onClick || onClose}
                  disabled={secondaryButton.disabled}
                >
                  {secondaryButton.text || 'Cancel'}
                </Button>
              )}
              {primaryButton && (
                <Button
                  variant="primary"
                  onClick={primaryButton.onClick || onClose}
                  disabled={primaryButton.disabled}
                >
                  {primaryButton.text || 'Done'}
                </Button>
              )}
            </div>
          )}
        </DialogPanel>
      </div>
    </Dialog>
  )
}

export default Modal
