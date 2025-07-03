import React, {useState} from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Box,
} from "@mui/material";
import {MagnifyingGlassPlusIcon, XIcon} from "@phosphor-icons/react";
import type {
  ClueConfig,
  EnvConfig,
  SutConfig,
} from "../../models/ResultsDetails";

const ConfigCard: React.FC<{
  title: string;
  data: EnvConfig | ClueConfig | SutConfig;
  subtext: string;
}> = ({title, data, subtext}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  return (
    <>
      <div className="border rounded-md mb-2 p-1 shadow-sm">
        <button
          onClick={handleOpenModal}
          className="w-full text-left p-2 bg-gray-50 hover:bg-gray-100 font-medium flex justify-between items-center transition-colors"
        >
          <div>
            <span>{title}</span>
            {subtext && <p className="text-xs text-gray-500">{subtext}</p>}
          </div>
          <div className="flex items-center">
            <MagnifyingGlassPlusIcon size={20} className="text-gray-600" />
          </div>
        </button>
      </div>

      <Dialog
        open={isModalOpen}
        onClose={handleCloseModal}
        maxWidth="md"
        fullWidth
        PaperProps={{
          className: "max-h-[80vh] rounded-lg shadow-xl",
        }}
      >
        <DialogTitle className="flex justify-between items-center p-4 border-b border-gray-200">
          <div>
            <span className="mb-2">{title}</span>
            {subtext && <p className="text-xs text-gray-500">{subtext}</p>}
          </div>
          <IconButton
            aria-label="close"
            onClick={handleCloseModal}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            <XIcon size={24} />
          </IconButton>
        </DialogTitle>

        <DialogContent className="p-6">
          <Box
            component="pre"
            className="bg-gray-50 p-4 rounded-md font-mono text-sm text-gray-800 whitespace-pre-wrap break-words overflow-auto"
          >
            {JSON.stringify(data, null, 2)}
          </Box>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ConfigCard;
