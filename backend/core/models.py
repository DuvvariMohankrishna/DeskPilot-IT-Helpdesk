import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class Department(models.Model):
    name=models.CharField(max_length=100, unique=True)
    description=models.TextField(blank=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name

class User(AbstractUser):
    class Role(models.TextChoices): ADMIN='ADMIN','Admin'; AGENT='AGENT','IT Support Agent'; EMPLOYEE='EMPLOYEE','Employee'
    email=models.EmailField(unique=True)
    phone=models.CharField(max_length=30, blank=True)
    employee_id=models.CharField(max_length=40, unique=True, null=True, blank=True)
    department=models.ForeignKey(Department,on_delete=models.SET_NULL,null=True,blank=True,related_name='users')
    role=models.CharField(max_length=12,choices=Role.choices,default=Role.EMPLOYEE)
    job_title=models.CharField(max_length=100,blank=True)
    @property
    def is_support_staff(self): return self.role in (self.Role.ADMIN,self.Role.AGENT)
    def save(self,*args,**kwargs):
        # createsuperuser does not know about our role field, so a superuser must always be an ADMIN
        if self.is_superuser and self.role!=self.Role.ADMIN: self.role=self.Role.ADMIN
        super().save(*args,**kwargs)
    def __str__(self): return self.get_full_name() or self.username

class TicketCategory(models.Model):
    name=models.CharField(max_length=80,unique=True)
    is_active=models.BooleanField(default=True)
    def __str__(self): return self.name

class AssetCategory(models.Model):
    name=models.CharField(max_length=80,unique=True)
    is_active=models.BooleanField(default=True)
    def __str__(self): return self.name

class Asset(models.Model):
    class Status(models.TextChoices): AVAILABLE='AVAILABLE','Available'; ASSIGNED='ASSIGNED','Assigned'; MAINTENANCE='MAINTENANCE','Under Maintenance'; DAMAGED='DAMAGED','Damaged'; LOST='LOST','Lost'; RETIRED='RETIRED','Retired'
    asset_tag=models.CharField(max_length=50,unique=True)
    name=models.CharField(max_length=150,blank=True)
    serial_number=models.CharField(max_length=100,blank=True)
    category=models.ForeignKey(AssetCategory,on_delete=models.PROTECT,related_name='assets')
    manufacturer=models.CharField(max_length=100,blank=True)
    model_name=models.CharField(max_length=100,blank=True)
    purchase_date=models.DateField(null=True,blank=True)
    purchase_price=models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    warranty_expiry=models.DateField(null=True,blank=True)
    status=models.CharField(max_length=15,choices=Status.choices,default=Status.AVAILABLE)
    location=models.CharField(max_length=150,blank=True)
    department=models.ForeignKey(Department,on_delete=models.SET_NULL,null=True,blank=True,related_name='assets')
    assigned_to=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='assigned_assets')
    notes=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self): return self.asset_tag
    @property
    def display_name(self): return self.name or ' '.join(filter(None,[self.manufacturer,self.model_name])) or self.asset_tag

class Ticket(models.Model):
    class Priority(models.TextChoices): LOW='LOW','Low'; MEDIUM='MEDIUM','Medium'; HIGH='HIGH','High'; CRITICAL='CRITICAL','Critical'
    class Status(models.TextChoices): NEW='NEW','New'; ASSIGNED='ASSIGNED','Assigned'; IN_PROGRESS='IN_PROGRESS','In Progress'; PENDING='PENDING','Pending'; RESOLVED='RESOLVED','Resolved'; CLOSED='CLOSED','Closed'; REOPENED='REOPENED','Reopened'
    ticket_number=models.CharField(max_length=14,unique=True,editable=False)
    title=models.CharField(max_length=200)
    description=models.TextField()
    category=models.ForeignKey(TicketCategory,on_delete=models.PROTECT,related_name='tickets')
    priority=models.CharField(max_length=10,choices=Priority.choices,default=Priority.MEDIUM)
    status=models.CharField(max_length=15,choices=Status.choices,default=Status.NEW)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='created_tickets')
    assigned_agent=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='assigned_tickets')
    department=models.ForeignKey(Department,on_delete=models.SET_NULL,null=True,blank=True,related_name='tickets')
    asset=models.ForeignKey(Asset,on_delete=models.SET_NULL,null=True,blank=True,related_name='tickets')
    resolution_notes=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    resolved_at=models.DateTimeField(null=True,blank=True)
    class Meta:
        ordering=['-created_at']
        indexes=[models.Index(fields=['status']),models.Index(fields=['priority']),models.Index(fields=['created_at'])]
    @staticmethod
    def generate_ticket_number():
        # Random suffix + existence check keeps numbers unique without a race-prone "max()+1".
        while True:
            number='HD-'+uuid.uuid4().hex[:8].upper()
            if not Ticket.objects.filter(ticket_number=number).exists(): return number
    def save(self,*args,**kwargs):
        if not self.ticket_number: self.ticket_number=self.generate_ticket_number()
        super().save(*args,**kwargs)
    def __str__(self): return self.ticket_number

class TicketComment(models.Model):
    ticket=models.ForeignKey(Ticket,on_delete=models.CASCADE,related_name='comments')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='ticket_comments')
    comment=models.TextField()
    is_internal=models.BooleanField(default=False,help_text='Internal support note, hidden from the ticket creator.')
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['created_at']

class TicketHistory(models.Model):
    ticket=models.ForeignKey(Ticket,on_delete=models.CASCADE,related_name='history')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='ticket_history')
    action=models.CharField(max_length=100)
    details=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['created_at']

class AssetHistory(models.Model):
    """Append-only audit trail for meaningful asset lifecycle changes."""
    asset=models.ForeignKey(Asset,on_delete=models.PROTECT,related_name='history')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='asset_history')
    action=models.CharField(max_length=100)
    details=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']
        indexes=[models.Index(fields=['asset','created_at'], name='core_asseth_asset_i_2f3b3a_idx')]
    def __str__(self): return f'{self.asset.asset_tag}: {self.action}'


class AssetAssignment(models.Model):
    asset=models.ForeignKey(Asset,on_delete=models.PROTECT,related_name='assignments')
    employee=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='asset_assignments')
    assigned_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='asset_assignments_made')
    assigned_at=models.DateTimeField(auto_now_add=True)
    returned_at=models.DateTimeField(null=True,blank=True)
    reason=models.CharField(max_length=250,blank=True)
    class Meta: ordering=['-assigned_at']

class AssetMaintenance(models.Model):
    class Status(models.TextChoices): OPEN='OPEN','Open'; COMPLETED='COMPLETED','Completed'
    asset=models.ForeignKey(Asset,on_delete=models.PROTECT,related_name='maintenance_records')
    maintenance_type=models.CharField(max_length=100)
    description=models.TextField()
    technician=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='maintenance_records')
    maintenance_date=models.DateField()
    cost=models.DecimalField(max_digits=12,decimal_places=2,default=0)
    result=models.CharField(max_length=30,choices=Status.choices,default=Status.COMPLETED)
    notes=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    recipient=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='notifications')
    message=models.CharField(max_length=250)
    ticket=models.ForeignKey(Ticket,on_delete=models.CASCADE,null=True,blank=True,related_name='notifications')
    asset=models.ForeignKey(Asset,on_delete=models.CASCADE,null=True,blank=True,related_name='notifications')
    is_read=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']
        indexes=[models.Index(fields=['recipient','is_read'])]
