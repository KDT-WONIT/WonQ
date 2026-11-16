import { BrowserQRCodeReader, type IScannerControls } from "@zxing/browser";
import { useEffect, useRef, useState } from "react";

export function QrScanner({ onScan }: { onScan: (value: string) => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!video.current) return;
    let finished = false;
    let controls: IScannerControls | undefined;
    const reader = new BrowserQRCodeReader();

    void reader.decodeFromVideoDevice(undefined, video.current, (result, _error, activeControls) => {
      if (!result || finished) return;
      finished = true;
      activeControls.stop();
      onScan(result.getText());
    }).then((activeControls) => {
      if (finished) activeControls.stop();
      else controls = activeControls;
    }).catch(() => {
      if (!finished) setError("카메라를 열 수 없습니다. 권한을 확인하거나 QR 값을 입력해 주세요.");
    });

    return () => {
      finished = true;
      controls?.stop();
    };
  }, [onScan]);

  return <div className="scanner">
    <video ref={video} muted playsInline aria-label="QR 카메라 미리보기" />
    {error && <p role="alert">{error}</p>}
  </div>;
}
