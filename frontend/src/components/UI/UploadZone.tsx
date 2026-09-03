// 📁 LOCATION: frontend/src/components/UI/UploadZone.tsx

"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { motion } from "framer-motion";
import { Upload } from "lucide-react";
import { useApp } from "@/context/AppContext";

export default function UploadZone() {
  const { uploadFiles, uploading } = useApp();

  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length) {
        uploadFiles(accepted);
      }
    },
    [uploadFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".jpg", ".jpeg", ".png", ".webp"],
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        ".docx",
      ],
      "text/plain": [".txt"],
    },
    maxSize: 50 * 1024 * 1024,
    disabled: uploading,
  });

  return (
    <div {...getRootProps()}>
      <motion.div
        whileHover={{ scale: uploading ? 1 : 1.01 }}
        className={`card border-2 border-dashed cursor-pointer transition-all duration-200 p-8 text-center
          ${
            isDragActive
              ? "border-brand-500 bg-brand-900/20"
              : "border-surface-border hover:border-brand-600/50 hover:bg-surface-hover"
          }
          ${uploading ? "pointer-events-none opacity-60" : ""}`}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-3">
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${
              isDragActive ? "bg-brand-600" : "bg-surface-hover"
            }`}
          >
            {uploading ? (
              <span className="animate-spin text-white text-xl">⟳</span>
            ) : (
              <Upload
                size={22}
                className={
                  isDragActive ? "text-white" : "text-gray-400"
                }
              />
            )}
          </div>

          <div>
            <p className="text-sm font-medium text-white">
              {uploading
                ? "Processing files..."
                : isDragActive
                ? "Drop files here"
                : "Drop files or click to upload"}
            </p>

            <p className="text-xs text-gray-500 mt-1">
              PDF, DOCX, Images, TXT — up to 50MB
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}