import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { motion } from "framer-motion";
import {
	App,
	Button,
	Card,
	Empty,
	Input,
	Modal,
	Popconfirm,
	Space,
	Spin,
	Typography,
} from "antd";
import {
	DeleteOutlined,
	EditOutlined,
	EyeOutlined,
	FilePdfOutlined,
	UploadOutlined,
} from "@ant-design/icons";
// Vite transforms this at build time — resolves to the worker file URL
const _pdfWorkerUrl = new URL(
	"pdfjs-dist/build/pdf.worker.min.mjs",
	import.meta.url,
).toString();

import {
	useCreateResume,
	useDeleteResume,
	useResumes,
	useUpdateResume,
} from "@/hooks/api";
import { useStaggerAnimation } from "@/hooks/useStaggerAnimation";
import type { UserResume } from "@/types";

interface ResumeManagerProps {
	onSelectResume?: (resume: UserResume) => void;
	selectedResumeId?: number;
}

export default function ResumeManager({
	onSelectResume,
	selectedResumeId,
}: ResumeManagerProps) {
	const message = App.useApp().message;
	const stagger = useStaggerAnimation(0.05, 0.05);
	const { data: resumes, isLoading, refetch } = useResumes();
	const createResume = useCreateResume();
	const updateResume = useUpdateResume();
	const deleteResume = useDeleteResume();
	const [uploadOpen, setUploadOpen] = useState(false);
	const [resumeName, setResumeName] = useState("");
	const [resumeText, setResumeText] = useState("");
	const [viewResume, setViewResume] = useState<UserResume | null>(null);
	const [editResume, setEditResume] = useState<UserResume | null>(null);
	const [editName, setEditName] = useState("");
	const [editText, setEditText] = useState("");
	const [pdfLoading, setPdfLoading] = useState(false);

	const handleUpload = async () => {
		if (!resumeName.trim()) {
			message.error("Please enter resume name");
			return;
		}
		if (!resumeText.trim()) {
			message.error("Please enter resume content");
			return;
		}
		try {
			await createResume.mutateAsync({
				name: resumeName.trim(),
				resume_text: resumeText.trim(),
			});
			message.success("Resume uploaded successfully");
			setUploadOpen(false);
			setResumeName("");
			setResumeText("");
			refetch();
		} catch {
			message.error("Upload failed");
		}
	};

	const handlePdfUpload = async (file: File) => {
		setPdfLoading(true);
		try {
			const pdfjs = await import("pdfjs-dist");
			pdfjs.GlobalWorkerOptions.workerSrc = _pdfWorkerUrl;

			const arrayBuffer = await file.arrayBuffer();
			const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;

			let fullText = "";
			for (let i = 1; i <= pdf.numPages; i++) {
				const page = await pdf.getPage(i);
				const content = await page.getTextContent();

				// Group items by y-position to form lines
				const linesMap = new Map<number, string[]>();
				for (const item of content.items) {
					const y = Math.round((item as { transform: number[] }).transform[5]);
					if (!linesMap.has(y)) linesMap.set(y, []);
					linesMap.get(y)!.push((item as { str: string }).str);
				}

				// Sort lines top to bottom
				const lines = Array.from(linesMap.entries())
					.sort(([yA], [yB]) => yB - yA)
					.map(([, items]) => items.join(" ").trim())
					.filter(Boolean);

				fullText += lines.join("\n") + "\n\n";
			}

			// Markdown conversion heuristics
			const unlikelyHeader = (text: string): boolean => {
				// Contains pipe separators (metadata bars like "男 | 电话")
				if (text.includes("|")) return true;
				// Has fullwidth Chinese punctuation (not a heading)
				if (/[：；！？、]/.test(text)) return true;
				// Email or @ symbol
				if (text.includes("@")) return true;
				// Date range pattern like "2018.11-2023.08" or "2018-2023"
				if (/\d{4}[.-]\d{1,2}[.-]?\d{0,2}?/.test(text)) return true;
				// Pure numbers or single characters
				if (/^[\d\s()（）]+$/.test(text)) return true;
				// Lines ending with colon → section labels, not headings
				if (/[:：]\s*$/.test(text)) return true;
				// Numbered list items like "1. xxx" or "1、xxx"
				if (/^\d+[.、]/.test(text.trimStart())) return true;
				return false;
			};

			const mdLines = fullText.split("\n").map((line) => {
				const trimmed = line.trim();
				if (!trimmed) return "";

				// Lines starting with bullet chars → - list items
				if (/^[•\-*▪►]\s*/.test(trimmed)) {
					return trimmed.replace(/^[•\-*▪►]\s*/, "- ");
				}

				// Short standalone line → section header (if it looks like one)
				if (
					trimmed.length < 50 &&
					!trimmed.includes("。") &&
					!trimmed.includes("，") &&
					!unlikelyHeader(trimmed)
				) {
					return `## ${trimmed}`;
				}

				return trimmed;
			});

			const markdown = mdLines
				.join("\n")
				.replace(/\n{3,}/g, "\n\n")
				.trim();

			setResumeText(markdown);

			// Auto-fill name from filename
			if (!resumeName.trim()) {
				setResumeName(file.name.replace(/\.pdf$/i, ""));
			}

			message.success(
				`PDF parsed: ${pdf.numPages} page(s), converted to Markdown`,
			);
		} catch (err) {
			console.error("PDF parse error:", err);
			message.error("Failed to parse PDF. Try copying text manually.");
		} finally {
			setPdfLoading(false);
		}
	};

	const handleDelete = async (id: number) => {
		try {
			await deleteResume.mutateAsync(id);
			message.success("Resume deleted");
			refetch();
		} catch {
			message.error("Delete failed");
		}
	};

	const openView = (resume: UserResume) => {
		setViewResume(resume);
	};

	const openEdit = (resume: UserResume) => {
		setEditResume(resume);
		setEditName(resume.name);
		setEditText(resume.resume_text);
	};

	const handleEdit = async () => {
		if (!editResume) return;
		if (!editName.trim()) {
			message.error("Please enter resume name");
			return;
		}
		if (!editText.trim()) {
			message.error("Please enter resume content");
			return;
		}
		try {
			await updateResume.mutateAsync({
				id: editResume.id,
				data: { name: editName.trim(), resume_text: editText.trim() },
			});
			message.success("Resume updated");
			setEditResume(null);
			refetch();
		} catch {
			message.error("Update failed");
		}
	};

	return (
		<Card title="Resume Management">
			<Space style={{ marginBottom: 16 }}>
				<Button
					type="primary"
					icon={<UploadOutlined />}
					onClick={() => setUploadOpen(true)}
				>
					Upload Resume
				</Button>
			</Space>

			{isLoading ? (
				<div style={{ textAlign: "center", padding: 24 }}>
					<Spin />
				</div>
			) : !resumes?.length ? (
				<Empty description="No resumes, please upload one first" />
			) : (
				<motion.div
					variants={stagger.container}
					initial="hidden"
					animate="show"
					style={{ display: "grid", gap: 12 }}
				>
					{resumes.map((resume) => (
						<motion.div key={resume.id} variants={stagger.item}>
							<Card
								size="small"
								title={resume.name}
								extra={
									<Space>
										{onSelectResume ? (
											<Button
												type={
													selectedResumeId === resume.id ? "primary" : "default"
												}
												size="small"
												onClick={() => onSelectResume(resume)}
											>
												{selectedResumeId === resume.id ? "Selected" : "Select"}
											</Button>
										) : null}
										<Button
											size="small"
											icon={<EyeOutlined />}
											onClick={() => openView(resume)}
										>
											View
										</Button>
										<Button
											size="small"
											icon={<EditOutlined />}
											onClick={() => openEdit(resume)}
										>
											Edit
										</Button>
										<Popconfirm
											title="Confirm delete this resume?"
											onConfirm={() => handleDelete(resume.id)}
										>
											<Button danger size="small" icon={<DeleteOutlined />}>
												Delete
											</Button>
										</Popconfirm>
									</Space>
								}
							>
								<Typography.Text type="secondary">
									Uploaded:{" "}
									{new Date(resume.created_at).toLocaleString("en-US")}
								</Typography.Text>
							</Card>
						</motion.div>
					))}
				</motion.div>
			)}

			<Modal
				title="Upload Resume"
				open={uploadOpen}
				onOk={handleUpload}
				onCancel={() => {
					setUploadOpen(false);
					setResumeName("");
					setResumeText("");
				}}
				confirmLoading={createResume.isPending || pdfLoading}
				width={720}
			>
				<Space orientation="vertical" style={{ width: "100%" }} size={16}>
					<div>
						<Typography.Text strong>Resume Name</Typography.Text>
						<Input
							aria-label="Resume Name"
							value={resumeName}
							onChange={(e) => setResumeName(e.target.value)}
							placeholder="e.g. Frontend Resume v1"
							style={{ marginTop: 6 }}
						/>
					</div>

					{/* PDF drop zone */}
					<div
						style={{
							border: "2px dashed var(--color-hairline)",
							borderRadius: 12,
							padding: 24,
							textAlign: "center",
							cursor: "pointer",
						}}
						onClick={() => document.getElementById("pdf-upload-input")?.click()}
						onDragOver={(e) => {
							e.preventDefault();
							e.currentTarget.style.borderColor = "var(--color-primary)";
						}}
						onDragLeave={(e) => {
							e.currentTarget.style.borderColor = "var(--color-hairline)";
						}}
						onDrop={(e) => {
							e.preventDefault();
							e.currentTarget.style.borderColor = "var(--color-hairline)";
							const file = e.dataTransfer?.files?.[0];
							if (file && file.type === "application/pdf") {
								handlePdfUpload(file);
							} else {
								message.warning("Please drop a PDF file");
							}
						}}
					>
						<input
							id="pdf-upload-input"
							type="file"
							accept=".pdf"
							style={{ display: "none" }}
							onChange={(e) => {
								const file = e.target.files?.[0];
								if (file) handlePdfUpload(file);
								e.target.value = "";
							}}
						/>
						{pdfLoading ? (
							<Spin />
						) : (
							<>
								<FilePdfOutlined
									style={{
										fontSize: 28,
										color: "var(--color-muted)",
										marginBottom: 8,
									}}
								/>
								<div
									style={{
										color: "var(--color-muted)",
										fontSize: 13,
									}}
								>
									Click or drag a PDF here to auto-convert to Markdown
								</div>
							</>
						)}
					</div>

					<Typography.Text type="secondary" style={{ fontSize: 12 }}>
						… or paste content manually below
					</Typography.Text>

					<div>
						<Typography.Text strong>Resume Content (Markdown)</Typography.Text>
						<Input.TextArea
							aria-label="Resume Content"
							value={resumeText}
							onChange={(e) => setResumeText(e.target.value)}
							placeholder="Paste or upload PDF to auto-convert to Markdown"
							autoSize={{ minRows: 12, maxRows: 20 }}
						/>
					</div>
				</Space>
			</Modal>

			{/* View Resume Modal — renders Markdown */}
			<Modal
				title={viewResume?.name || "View Resume"}
				open={!!viewResume}
				onCancel={() => setViewResume(null)}
				footer={<Button onClick={() => setViewResume(null)}>Close</Button>}
				width={720}
			>
				<div
					style={{
						background: "var(--color-surface-soft)",
						padding: 20,
						borderRadius: 8,
						fontSize: 14,
						lineHeight: 1.7,
						overflowY: "auto",
						maxHeight: 500,
					}}
				>
					<ReactMarkdown
						components={{
							h1: ({ ...props }) => (
								<h1
									style={{
										fontSize: 20,
										fontWeight: 600,
										margin: "16px 0 8px",
									}}
									{...props}
								/>
							),
							h2: ({ ...props }) => (
								<h2
									style={{
										fontSize: 16,
										fontWeight: 600,
										margin: "14px 0 6px",
									}}
									{...props}
								/>
							),
							ul: ({ ...props }) => (
								<ul style={{ paddingLeft: 20, margin: "6px 0" }} {...props} />
							),
							li: ({ ...props }) => (
								<li style={{ marginBottom: 4 }} {...props} />
							),
							p: ({ ...props }) => <p style={{ margin: "6px 0" }} {...props} />,
						}}
					>
						{viewResume?.resume_text || ""}
					</ReactMarkdown>
				</div>
			</Modal>

			{/* Edit Resume Modal */}
			<Modal
				title={`Edit: ${editResume?.name || ""}`}
				open={!!editResume}
				onOk={handleEdit}
				onCancel={() => setEditResume(null)}
				confirmLoading={updateResume.isPending}
				width={720}
				okText="Save"
			>
				<Space orientation="vertical" style={{ width: "100%" }} size={16}>
					<div>
						<Typography.Text strong>Resume Name</Typography.Text>
						<Input
							aria-label="Edit Resume Name"
							value={editName}
							onChange={(e) => setEditName(e.target.value)}
							placeholder="e.g. Frontend Resume v1"
							style={{ marginTop: 6 }}
						/>
					</div>
					<div>
						<Typography.Text strong>Resume Content</Typography.Text>
						<Input.TextArea
							aria-label="Edit Resume Content"
							value={editText}
							onChange={(e) => setEditText(e.target.value)}
							placeholder="Edit resume content"
							autoSize={{ minRows: 12, maxRows: 20 }}
						/>
					</div>
				</Space>
			</Modal>
		</Card>
	);
}
