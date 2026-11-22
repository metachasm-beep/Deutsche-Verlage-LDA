import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { HelpCircle } from 'lucide-react';
import clsx from 'clsx';

export interface InfoTooltipProps {
  /** Short bold heading inside the tooltip (optional) */
  title?: string;
  /** Plain-English explanation shown on hover/focus */
  content: string;
  /** Optional wrapped element; if omitted, renders a compact (?) help badge */
  children?: React.ReactNode;
  /** Preferred placement relative to trigger */
  placement?: 'top' | 'bottom' | 'left' | 'right';
  /** Extra classes on wrapper span */
  className?: string;
  /** Render a small inline (?) icon next to children */
  showIcon?: boolean;
  /** Maximum width in pixels */
  maxWidth?: number;
}

/**
 * Portal-rendered hover & keyboard-focus tooltip that never clips inside
 * scrollable drawers, tables, or overflow-hidden panels, and automatically
 * adapts to both Dark Obsidian and Light Parchment themes.
 */
export const InfoTooltip: React.FC<InfoTooltipProps> = ({
  title,
  content,
  children,
  placement = 'top',
  className,
  showIcon = false,
  maxWidth = 280,
}) => {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number; actualPlacement: 'top' | 'bottom' }>({
    top: 0,
    left: 0,
    actualPlacement: placement === 'bottom' ? 'bottom' : 'top',
  });
  const triggerRef = useRef<HTMLSpanElement | null>(null);
  const timerRef = useRef<number | null>(null);

  const updatePosition = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const estHeight = title ? 92 : 68;
    const margin = 10;

    let actualPlacement: 'top' | 'bottom' = placement === 'bottom' ? 'bottom' : 'top';
    if (actualPlacement === 'top' && rect.top < estHeight + 16) {
      actualPlacement = 'bottom';
    } else if (actualPlacement === 'bottom' && vh - rect.bottom < estHeight + 16) {
      actualPlacement = 'top';
    }

    const halfW = maxWidth / 2;
    let centerX = rect.left + rect.width / 2;
    if (centerX - halfW < margin) centerX = halfW + margin;
    if (centerX + halfW > vw - margin) centerX = vw - halfW - margin;

    const top = actualPlacement === 'top' ? rect.top - 8 : rect.bottom + 8;
    setCoords({ top, left: centerX, actualPlacement });
  }, [placement, maxWidth, title]);

  const handleOpen = () => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    updatePosition();
    timerRef.current = window.setTimeout(() => {
      updatePosition();
      setOpen(true);
    }, 110);
  };

  const handleClose = () => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    setOpen(false);
  };

  useEffect(() => {
    if (!open) return;
    const onScrollOrResize = () => updatePosition();
    window.addEventListener('scroll', onScrollOrResize, true);
    window.addEventListener('resize', onScrollOrResize);
    return () => {
      window.removeEventListener('scroll', onScrollOrResize, true);
      window.removeEventListener('resize', onScrollOrResize);
    };
  }, [open, updatePosition]);

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, []);

  const tooltipNode =
    open && typeof document !== 'undefined'
      ? createPortal(
          <div
            role="tooltip"
            style={{
              position: 'fixed',
              top: coords.top,
              left: coords.left,
              maxWidth,
              transform:
                coords.actualPlacement === 'top'
                  ? 'translate(-50%, -100%)'
                  : 'translate(-50%, 0%)',
              zIndex: 9999,
            }}
            className="pointer-events-none px-3 py-2 rounded-lg bg-obsidian-900 border border-traditional/45 shadow-2xl text-left backdrop-blur-xl transition-opacity duration-150"
          >
            {title && (
              <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-traditional mb-1">
                {title}
              </div>
            )}
            <p className="font-sans text-[11px] leading-relaxed text-parchment-100">
              {content}
            </p>
          </div>,
          document.body
        )
      : null;

  return (
    <>
      <span
        ref={triggerRef}
        onMouseEnter={handleOpen}
        onMouseLeave={handleClose}
        onFocus={handleOpen}
        onBlur={handleClose}
        tabIndex={children ? undefined : 0}
        className={clsx(
          'inline-flex items-center gap-1',
          !children && 'cursor-help text-parchment-300 hover:text-traditional transition-colors align-middle',
          className
        )}
      >
        {children}
        {(!children || showIcon) && (
          <HelpCircle
            className="w-3.5 h-3.5 text-parchment-300/80 hover:text-traditional transition-colors shrink-0 cursor-help"
            aria-label={title || 'Explanation'}
          />
        )}
      </span>
      {tooltipNode}
    </>
  );
};
