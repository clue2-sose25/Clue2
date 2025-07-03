import React, {useState} from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
  Box,
} from "@mui/material";
import {MagnifyingGlassPlusIcon, XIcon} from "@phosphor-icons/react";

const ConfigCard: React.FC<{title: string; data: any}> = ({title, data}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  return (
    <>
      <div className="border rounded mb-2 bg-white border rounded-sm p-1">
        <button
          onClick={handleOpenModal}
          className="w-full text-left p-3 bg-gray-50 hover:bg-gray-100 font-medium flex justify-between items-center"
        >
          {title}
          <div className="flex gap-2 items-center">
            <MagnifyingGlassPlusIcon size={20} />
          </div>
        </button>
      </div>

      <Dialog
        open={isModalOpen}
        onClose={handleCloseModal}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            minHeight: "60vh",
            maxHeight: "80vh",
          },
        }}
      >
        <DialogTitle
          sx={{
            m: 0,
            p: 2,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          {title}
          <IconButton
            aria-label="close"
            onClick={handleCloseModal}
            sx={{color: (theme) => theme.palette.grey[500]}}
          >
            <XIcon size={24} />
          </IconButton>
        </DialogTitle>

        <DialogContent dividers sx={{p: 3}}>
          <Box
            component="pre"
            sx={{
              fontSize: "0.875rem",
              overflow: "auto",
              backgroundColor: "grey.50",
              p: 2,
              borderRadius: 1,
              fontFamily: "monospace",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              margin: 0,
            }}
          >
            {JSON.stringify(data, null, 2)}
          </Box>
        </DialogContent>

        <DialogActions sx={{p: 2}}>
          <Button onClick={handleCloseModal} color="primary">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default ConfigCard;
