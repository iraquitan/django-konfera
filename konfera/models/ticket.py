from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from konfera.models.abstract import KonferaModel
from konfera.models.order import Order
from konfera.models.speaker import Speaker


class Ticket(KonferaModel):
    REQUESTED = 'requested'
    REGISTERED = 'registered'
    CHECKEDIN = 'checked-in'
    CANCELLED = 'cancelled'

    TICKET_STATUS = (
        (REQUESTED, _('Requested')),
        (REGISTERED, _('Registered')),
        (CHECKEDIN, _('Checked-in')),
        (CANCELLED, _('Cancelled')),
    )

    type = models.ForeignKey('TicketType')
    discount_code = models.ForeignKey('DiscountCode', blank=True, null=True)
    status = models.CharField(choices=TICKET_STATUS, max_length=32)
    title = models.CharField(choices=Speaker.TITLE_CHOICES, max_length=4, default=Speaker.TITLE_UNSET)
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    email = models.EmailField()
    phone = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    order = models.ForeignKey('Order', blank=True)

    def __str__(self):
        return '{title} {first_name} {last_name}'.format(
            title=dict(Speaker.TITLE_CHOICES)[self.title],
            first_name=self.first_name,
            last_name=self.last_name
        ).strip()

    def discount_calculator(self):

        if self.discount_code:
            return self.type.price * self.discount_code.discount / 100
        return 0

    def clean(self):
        if self.discount_code and self.discount_code.ticket_type != self.type:
            raise ValidationError(
                {'discount_code': _('Discount code is not applicable for the selected ticket type.')})
        if hasattr(self, 'order'):
            exist_ticket = self.order.ticket_set.first()
            if exist_ticket and exist_ticket.type.event.id != self.type.event.id:
                raise ValidationError(_('All tickets must be for the same event.'))
        super().clean()

    def save(self, *args, **kwargs):
        self.clean()
        if not hasattr(self, 'order'):
            discount = self.discount_calculator()
            order = Order(price=self.type.price, discount=discount, status=Order.AWAITING,
                          purchase_date=timezone.now())
            order.save()
            self.order = order
        super(Ticket, self).save(*args, **kwargs)
